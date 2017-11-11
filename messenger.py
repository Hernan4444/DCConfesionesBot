import requests


class Messenger():
    def __init__(self, bot_token, admin_group, public_group, channel):
        self.bot_token = bot_token
        self.admin_group = admin_group
        self.public_group = public_group
        self.channel = channel

    def send_message(self, text, group, markdown=False):
        url = "https://api.telegram.org/bot{}/".format(self.bot_token)
        params = {
            "method": "sendMessage",
            "text": text,
            "chat_id": group,
        }
        if markdown:
            params["parse_mode"] = "Markdown"
            params["disable_web_page_preview"] = "True"
        return requests.get(url, params=(params))

    def send_admin(self, text, markdown=False):
        return self.send_message(text, self.admin_group, markdown)

    def send_public(self, text, markdown=False):
        self.send_message(text, self.public_group, markdown)
        self.send_message(text, self.channel, markdown)
