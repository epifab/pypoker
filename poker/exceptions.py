class GameError(Exception):
    pass


class HandFailException(Exception):
    pass


class SocketError(Exception):
    pass


class MessageTimeout(Exception):
    pass


class MessageFormatError(Exception):
    def __init__(self, attribute=None, desc=None, expected=None, found=None):
        message = "Invalid message received."
        if attribute:
            message += " Invalid message attribute {}.".format(attribute)
            if expected is not None and found is not None:
                message += " '{}' expected, found '{}'.".format(attribute, expected, found)
        if desc:
            message += " " + desc
        Exception.__init__(self, message)

    @staticmethod
    def validate_msg_id(message, expected):
        if "msg_id" not in message:
            raise MessageFormatError(attribute="msg_id", desc="Attribute is missing")
        elif message["msg_id"] == "error":
            if "error" in message:
                raise MessageFormatError(desc="Error received from the remote host: '{}'".format(message['error']))
            else:
                raise MessageFormatError(desc="Unknown error received from the remote host")
        if message["msg_id"] != expected:
            raise MessageFormatError(attribute="msg_id", expected=expected, found=message["msg_id"])
