from configparser import ExtendedInterpolation

from nacl.encoding import Base64Encoder
from nacl.public import PublicKey, PrivateKey
from nacl.signing import SigningKey, VerifyKey


class KeyInterpolation(ExtendedInterpolation):
    def before_get(self, parser, section, option, value, defaults):
        value = super().before_get(parser, section, option, value, defaults)

        if option.endswith('_public_key'):
            return PublicKey(value.encode('utf-8'), encoder=Base64Encoder)
        elif option.endswith('_private_key'):
            return PrivateKey(value.encode('utf-8'), encoder=Base64Encoder)
        elif option.endswith('_signing_key'):
            return SigningKey(value.encode('utf-8'), encoder=Base64Encoder)
        elif option.endswith('_verify_key'):
            return VerifyKey(value.encode('utf-8'), encoder=Base64Encoder)

        return value
