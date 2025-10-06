тут использвуется uv вместо pip. Тк uv быстрее и удобнее.

скачать uv: https://docs.astral.sh/uv/getting-started/installation/#standalone-installer

синхронизировать библиотеки с pyproject.toml : uv sync

запустить код: uv run go.py

Eсть шанс того что у вас не запуститься. T.к я работал на линукс и папки venv разные. Вам тогда надо будет удалить папку venv и прописать uv sync.