"""Duas versões de prompt privado, sem chamar modelo; pull por commit imutável."""

import hashlib
from uuid import uuid4

from _common import parser, session, write_json

V1 = "Explique a evidência: {evidence}"
V2 = "Explique apenas fatos de {evidence}. Marque lacunas. A recomendação não aprova nem executa mudanças."


def main():
    args = parser(__doc__).parse_args()
    with session(args, lab="13-prompts") as client:
        from langchain_core.prompts import ChatPromptTemplate

        info = {"v1_sha256": hashlib.sha256(V1.encode()).hexdigest(),
                "v2_sha256": hashlib.sha256(V2.encode()).hexdigest()}
        first = ChatPromptTemplate.from_messages([("system", V1)])
        second = ChatPromptTemplate.from_messages([("system", V2)])
        if client:
            name = f"dcra-estudo-prompt-{uuid4().hex[:10]}"
            url1 = client.push_prompt(name, object=first, is_public=False)
            commit1 = client.pull_prompt_commit(name, skip_cache=True).commit_hash
            url2 = client.push_prompt(name, object=second, is_public=False)
            commit2 = client.pull_prompt_commit(name, skip_cache=True).commit_hash
            pinned = client.pull_prompt(f"{name}:{commit1}", skip_cache=True)
            rendered = pinned.invoke({"evidence": "usage=UNAVAILABLE"}).to_messages()[0].content
            if rendered != V1.format(evidence="usage=UNAVAILABLE"):
                raise RuntimeError("Pull da v1 não corresponde ao conteúdo esperado.")
            info |= {"name": name, "commit_v1": commit1, "commit_v2": commit2,
                     "url_v1": url1, "url_v2": url2}
            print(url1, url2, sep="\n")
            print("Mesmo após publicar v2, pull por commit da v1 retornou:", rendered)
        else:
            print("v1:", first.invoke({"evidence": "usage=UNAVAILABLE"}).to_messages()[0].content)
            print("v2:", second.invoke({"evidence": "usage=UNAVAILABLE"}).to_messages()[0].content)
            print("Hashes de conteúdo distintos:", info)
        write_json("13-prompts.json", info)


if __name__ == "__main__":
    main()
