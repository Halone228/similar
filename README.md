# Similar bot
Находит и группирует похожие по смыслу предложения. Использует эксель для импорта и экспорта данных.
## Запуск
**Установить [uv](https://docs.astral.sh/uv/getting-started/installation/)**

Linux & MacOS

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Windows
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```
При проблемах с установкой обращаться к документации [uv](https://docs.astral.sh/uv/getting-started/installation/)

**Синхронизация пакетов**
```bash
uv sync
```
**Проверка работы**
```bash
uv run main.py --help
```
```bash
uv run main.py -i input.xlsx -o output.xlsx
```
## Работа с программой
```bash
Options:
  -i, --input PATH
  -o, --output PATH
  -m, --model TEXT
  -t, --threshold FLOAT  Параметр близости
  -p, --progress         Показывать прогресс
  --help                 Show this message and exit.
```
