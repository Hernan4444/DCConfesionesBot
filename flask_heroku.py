# coding=utf-8
from messenger import Messenger
from flask import Flask, request
from json import loads as load_json
import os
import re

# env vars
TOKEN = os.environ["token"]
admin_group = int(os.environ["admin_group"])
public_group = int(os.environ["public_group"])
channel = int(os.environ["channel"])
groups = (admin_group, public_group)

app = Flask(__name__)
messages = {}
cmd = r"(/[a-zA-Z]*)(?:\s)?(.*)"


def id_generator():
    n = 1
    while True:
        yield n
        n += 1


message_id = id_generator()

# Responses
resp = {
    "completed": "Action Completed",
    "ignored": "Action Ignored",
    "error": "Error",
}

# Templates
template_admin = "*Nuevo Mensaje\tid:* {}\n{}"
template_public = "*DCConfesión #{} * \n{}"
template_admin_message = "*Admin:* {}"

messenger = Messenger(TOKEN, admin_group, public_group, channel)

tag_message = 1
messenger.send_admin("*Me han reiniciado :(*", True)


@app.route("/Bot", methods=["POST", "GET"])
def telegram_bot():
    try:
        request_data = load_json(request.data)

        if "edited_message" in request_data:
            return resp["ignored"]

        chat_id = int(request_data["message"]["chat"]["id"])
        text = str(request_data["message"]["text"])

        # Un nuevo mensaje que no de ninguno de los dos grupos
        if chat_id not in groups and not text.startswith("/"):
            # le mando el mensaje a los admin y guardo este con un id único
            id_ = next(message_id)
            messages[id_] = text
            messenger.send_admin(template_admin.format(
                str(id_),
                text
            ), True)
            return resp["completed"]

        # Si el mensaje viene del grupo de admin
        elif chat_id == admin_group:
            match = re.search(cmd, text)
            if not match:
                return resp["ignored"]

            command = match.group(1)
            argument = match.group(2)

            def get_message(id_):
                id_ = int(id_)
                if id_ in messages:
                    messenger.send_admin(messages[id_])

            def get_all_messages(_):
                if not messages:
                    messenger.send_admin("No hay mensajes pendientes")
                else:
                    text = ", ".join([str(k) for k in messages])
                    messenger.send_admin(text)

            def set_tag(new_id):
                global tag_message
                tag_message = int(new_id)
                messenger.send_admin(
                    "ID de los mensajes seteado en {}".format(tag_message),
                )

            def admin_response(text):
                message = template_admin_message.format(text)
                messenger.send_public(message, True)

            def approve_message(id_):
                if not id_:
                    return

                global tag_message
                id_ = int(id_)
                if id_ not in messages:
                    return
                message = template_public.format(
                    tag_message,
                    messages[id_]
                )
                messenger.send_public(message, True)
                del messages[id_]
                tag_message += 1

            def reject_messages(argument):
                if not argument:
                    return
                elif argument == "all":
                    messages.clear()
                    messenger.send_admin("Mensajes eliminados", True)
                    return
                else:
                    id_ = int(argument)
                    if id_ not in messages:
                        return
                    del messages[id_]
                    messenger.send_admin(
                        "Mensaje con id {} fue rechazado".format(id_),
                        True,
                    )

            def wrong_command(_):
                messenger.send_admin("No existe este comando", True)

            try:
                {
                    "/get": get_message,
                    "/all": get_all_messages,
                    "/set": set_tag,
                    "/r": admin_response,
                    "/yes": approve_message,
                    "/no": reject_messages,
                }.get(command, wrong_command)(argument)
            except ValueError:
                messenger.send_admin(
                    "No se pudo procesar el comando",
                    True,
                 )
            return resp["completed"]

        return resp["ignored"]

    except Exception as e:
        print("ERROR EN EL BOT\n{}".format(e))
        # Si es que se genera un error que no deja aceptar más mensajes
        return resp["error"]


if __name__ == "__main__":
    app.run()
