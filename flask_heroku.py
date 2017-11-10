# coding=utf-8
from flask import Flask, request
from json import loads as load_json
import os
import re
import requests

# env vars
TOKEN = os.environ["token"]
admin_group = int(os.environ["admin_group"])
public_group = int(os.environ["public_group"])
channel = int(os.environ["channel"])

groups = (admin_group, public_group)

app = Flask(__name__)
messages = {}
cmd = r"(/[a-zA-Z]*)(?:\s)?(\S*)"


def id_generator():
    n = 1
    while True:
        yield n
        n += 1


message_id = id_generator()


def send_message(text, id_, markdown=False):
    url = "https://api.telegram.org/bot{}/".format(TOKEN)
    params = {
        "method": "sendMessage",
        "text": text,
        "chat_id": id_,
    }
    if markdown:
        params["parse_mode"] = "Markdown"
        params["disable_web_page_preview"] = "True"
    return requests.get(url, params=(params))


# Responses

resp = {
    "completed": "Action Completed",
    "ignored": "Action Ignored",
}

# Templates
template_admin = "*Nuevo Mensaje\tid:* {}\n{}"
template_public = "*DCConfesión #{} * \n{}"
template_admin_message = "*Admin:* {}"

tag_message = 1
send_message("*Me han reiniciado :(*", admin_group, True)


@app.route('/Bot', methods=["POST", "GET"])
def telegram_bot():
    try:
        request_data = load_json(request.data)

        if "edited_message" in request_data:
            return resp['ignored']

        chat_id = int(request_data["message"]["chat"]["id"])
        text = str(request_data["message"]["text"])

        # Un nuevo mensaje que no de ninguno de los dos grupos
        if chat_id not in groups and not text.startswith("/"):
            # le mando el mensaje a los admin y guardo este con un id único
            id_ = next(message_id)
            messages[id_] = text
            send_message(template_admin.format(
                str(id_),
                text
            ), admin_group, True)
            return resp['completed']

        # Si el mensaje viene del grupo de admin
        elif chat_id == admin_group:
            match = re.search(cmd, text)
            if not match:
                return resp['ignored']

            command = match.group(1)
            argument = match.group(2)

            def get_message(id_):
                if int(id_) in messages:
                    send_message(messages[id_], admin_group)

            def get_all_messages(_):
                if not messages:
                    send_message("No hay mensajes pendientes", admin_group)
                else:
                    text = ", ".join([str(k) for k in messages])
                    send_message(text, admin_group)

            def set_tag(new_id):
                global tag_message
                tag_message = int(new_id)
                send_message(
                    "ID de los mensajes seteado en {}".format(tag_message),
                    admin_group,
                )

            def admin_response(text):
                message = template_admin_message.format(text)
                send_message(message, public_group, True)
                send_message(message, channel, True)

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
                send_message(message, public_group, True)
                send_message(message, channel, True)
                del messages[id_]
                tag_message += 1

            def reject_messages(_):
                if not argument:
                    return
                elif argument == 'all':
                    messages.clear()
                    send_message("Mensajes eliminados", admin_group, True)
                    return
                else:
                    id_ = int(argument)
                    if id_ not in messages:
                        return
                    del messages[id_]
                    send_message(
                        "Mensaje con id {} fue rechazado".format(id_),
                        admin_group,
                        True,
                    )

            def wrong_command(_):
                send_message("No existe este comando", admin_group, True)

            try:
                {
                    '/get': get_message,
                    '/all': get_all_messages,
                    '/set': tag_message,
                    '/r': admin_response,
                    '/yes': approve_message,
                    '/no': reject_messages,
                }.get(command, wrong_command)(argument)
            except ValueError:
                send_message(
                    "No se pudo procesar el comando",
                    admin_group,
                    True,
                 )
            return resp['completed']

    except Exception as e:
        print("ERROR EN EL BOT\n{}".format(e))
        # Si es que se genera un error que no deja aceptar más mensajes
        return "Error"


if __name__ == '__main__':
    app.run()
