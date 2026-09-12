"""Execute primeiro: versões e presença de credenciais, sem imprimir segredos."""

from _common import configure, credential_present, manifest, parser, write_json
from packaging.version import Version

SDK_MINIMO = "0.12.4"  # primeira versão em que a API v2 do SDK funciona neste ambiente (ver capítulo 27)


def main():
    args = parser(__doc__).parse_args()
    configure(args)
    import os

    info = manifest()
    print(f"Python: {info['python']}")
    print(f"Pacotes: {info['packages']}")
    if Version(info["packages"]["langsmith"]) < Version(SDK_MINIMO):
        # Abaixo disso o cliente v2 (client.runs.*, usado pelos labs 01-17) falha ao conectar quando
        # `httpx2` também está instalado: o SDK mistura as duas bibliotecas HTTP ao montar o timeout.
        print(f"AVISO: langsmith {info['packages']['langsmith']} < {SDK_MINIMO}; rode `uv lock "
              "--upgrade-package langsmith && uv sync` antes dos modos --send.")
    for name in ["LANGSMITH_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"]:
        print(f"{name}: {'configurada' if credential_present(name) else 'ausente/placeholder'}")
    print(f"Projeto de estudo: {args.project}")
    print(f"Endpoint personalizado: {'sim' if os.getenv('LANGSMITH_ENDPOINT') else 'não (padrão SDK)'}")
    print("Este diagnóstico não autentica nem envia dados, mesmo com --send.")
    write_json("manifesto.json", info)


if __name__ == "__main__":
    main()
