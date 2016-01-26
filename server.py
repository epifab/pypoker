from poker import Server
import logging


def main():
    pass

if __name__ == '__main__':
    host = "localhost"
    port = 9000

    logging.basicConfig(level=logging.INFO)

    logger = logging.getLogger("pypoker-server")
    logger.setLevel(level=logging.INFO)

    server = Server(host=host, port=port, logger=logger)
    server.start()
