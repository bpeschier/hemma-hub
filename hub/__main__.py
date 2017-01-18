import argparse
import asyncio
import logging
import sys
from configparser import ConfigParser

from nacl.encoding import Base64Encoder
from nacl.public import PrivateKey
from nacl.signing import SigningKey

from . import Hub
from .config import KeyInterpolation

parser = argparse.ArgumentParser(
    description='Central hub for hemma'
)

parser.add_argument(
    '--config',
    '-c',
    dest='config',
    default='hemma.conf',
)

parser.add_argument(
    '--debug',
    '-d',
    dest='debug',
    action='store_true',
    default=False,
)

parser.add_argument(
    '-u',
    '--upstream',
    dest='port',
    type=str,
    action='store',
    default=None,
)

parser.add_argument(
    '-g',
    '--generate-keys',
    dest='generate',
    action='store_true',
    default=False,
)

args = parser.parse_args()

loop = asyncio.get_event_loop()

log_level = logging.DEBUG if args.debug else logging.INFO
logger = logging.getLogger()
logger.setLevel(log_level)

# create logging handler and set level to debug argument
ch = logging.StreamHandler(sys.stdout)

ch.setLevel(log_level)

# create formatter
formatter = logging.Formatter('{name: <25} {levelname: <8} | {message}', style='{')

# add formatter to ch
ch.setFormatter(formatter)

# add ch to logger
logger.addHandler(ch)

# Check if we just need to generate keys
if args.generate:
    private_key = PrivateKey.generate()
    signing_key = SigningKey.generate()
    print('Public/private keys')
    print(private_key.encode(Base64Encoder).decode('utf-8'))
    print(private_key.public_key.encode(Base64Encoder).decode('utf-8'))
    print('')
    print('Signing key seed')
    print(signing_key.encode(Base64Encoder).decode('utf-8'))
    print(signing_key.verify_key.encode(Base64Encoder).decode('utf-8'))

else:

    loop.set_debug(args.debug)

    config = ConfigParser(interpolation=KeyInterpolation())
    with open(args.config, 'r') as f:
        config.read_file(f)

    hub = Hub(config)

    try:
        hub.add_tasks(loop)
        loop.run_forever()
    finally:

        # We need to clean up a bit
        pending = asyncio.Task.all_tasks()
        for t in pending:
            t.cancel()

        loop.run_until_complete(asyncio.gather(*pending))
