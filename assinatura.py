from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

TAMANHO_CHAVE = 2048
EXPOENTE_PUBLICO = 65537
_PSS = padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH)


def gerar_par():
    return rsa.generate_private_key(public_exponent=EXPOENTE_PUBLICO, key_size=TAMANHO_CHAVE)


def privada_para_pem(chave) -> str:
    return chave.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()


def publica_para_pem(chave) -> str:
    return chave.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()


def carregar_privada(pem: str):
    return serialization.load_pem_private_key(pem.encode(), password=None)


def assinar(chave_privada, mensagem: bytes) -> str:
    return chave_privada.sign(mensagem, _PSS, hashes.SHA256()).hex()


def verificar(chave_publica_pem: str, mensagem: bytes, assinatura_hex: str) -> bool:
    try:
        chave = serialization.load_pem_public_key(chave_publica_pem.encode())
        chave.verify(bytes.fromhex(assinatura_hex), mensagem, _PSS, hashes.SHA256())
        return True
    except (InvalidSignature, ValueError):
        return False
