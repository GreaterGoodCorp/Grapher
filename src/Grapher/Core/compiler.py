import os
import dill
import hmac
import base64
from py import code

from Grapher.Core import generate_ast


class Compiler:
    @staticmethod
    def compile(source: str) -> bytes:
        """Compiles Grapher source code to Grapher bytecode.

        :param source: Grapher source code.
        :type source: str
        :return: Grapher bytecode.
        :rtype: bytes
        """
        ast = generate_ast(source)
        bytecode = Compiler.__compile(ast.codify())
        signature = Compiler.__sign(bytecode, True)
        return bytecode + signature

    @staticmethod
    def decompile(source: bytes, unsafe: bool = False) -> code:
        """Decompile Grapher bytecode to Python bytecode.

        :param source: Grapher bytecode.
        :type source: bytes
        :param unsafe: Whether to enable unsafe decompilation.
        :type unsafe: bytes
        :return: Python bytecode.
        :rtype: code
        """
        bytecode, signature = source[:-64], source[-64:]
        try:
            ctrl_signature = Compiler.__sign(bytecode, False)
            assert hmac.compare_digest(signature, ctrl_signature)
        except UnverifiedSignatureWarning:
            if not unsafe:
                raise UnsafeDecompilationError("No signing key found.")
            else:
                warnings.warn("No signing key found. Signature verification will be skipped.")
        except AssertionError:
            if not unsafe:
                raise UnsafeDecompilationError("Signature verification failed.")
            else:
                warnings.warn("Signature verification failed. Proceed with execution carefully.")
        try:
            return Compiler.__decompile(bytecode)
        except (EOFError, ValueError, TypeError):
            raise ValueError("Grapher bytecode cannot be decompiled due to data corruption.")

    @staticmethod
    def get_signing_key():
        return Compiler.__get_random_signature_key()

    @staticmethod
    def __compile(source):
        return dill.dumps(compile(source, "<Grapher>", "exec", optimize=2))

    @staticmethod
    def __decompile(bytecode):
        return dill.loads(bytecode)

    @staticmethod
    def __sign(source, is_compile):
        return hmac.new(Compiler.__get_signature_key(is_compile), source, "sha512").digest()

    @staticmethod
    def __get_signature_key(is_compile):
        s = os.getenv("GRAPHER_SIGNING_KEY")
        if s is not None:
            return base64.b64decode(s)
        if is_compile:
            warnings.warn("No singing key found, a random key is used.", UnverifiedSignatureWarning)
            return Compiler.__get_random_signature_key()
        else:
            raise UnverifiedSignatureWarning

    @staticmethod
    def __get_random_signature_key():
        return os.urandom(32)


class UnverifiedSignatureWarning(Warning):
    def __init__(self, *args):
        super(UnverifiedSignatureWarning, self).__init__(*args)


class UnsafeDecompilationError(BaseException):
    def __init__(self, *args):
        super(UnsafeDecompilationError, self).__init__(*args)


def execute(source) -> None:
    """Executes Grapher source code. This function is dangerous and used for debugging purposes only."""
    s = Compiler.compile(source)
    exec(Compiler.decompile(s, True))
