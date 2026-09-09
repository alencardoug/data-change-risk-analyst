"""Execute primeiro: versões e presença de credenciais, sem imprimir segredos."""

from _common import configure, credential_present, manifest, parser, write_json


def main():
    args = parser(__doc__).parse_args()
    configure(args)
    import os

    info = manifest()
    print(f"Python: {info['python']}")
    print(f"Pacotes: {info['packages']}")
    for name in ["LANGSMITH_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"]:
        print(f"{name}: {'configurada' if credential_present(name) else 'ausente/placeholder'}")
    print(f"Projeto de estudo: {args.project}")
    print(f"Endpoint personalizado: {'sim' if os.getenv('LANGSMITH_ENDPOINT') else 'não (padrão SDK)'}")
    print("Este diagnóstico não autentica nem envia dados, mesmo com --send.")
    write_json("manifesto.json", info)


if __name__ == "__main__":
    main()
