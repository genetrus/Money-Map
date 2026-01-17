# Money Map

Данные, правила и визуализация для карты способов заработка. Проект строится вокруг:

- универсальной формулы (что продаём / кому / за какую меру ценности),
- матрицы 2×2×2 (активность × масштабируемость × риск),
- таксономии из 14 механизмов дохода,
- мостов и типовых переходов между ячейками.

## Быстрый старт

### Bash (Linux/macOS)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .

money-map validate
money-map axes
money-map cells
money-map cell A1
money-map taxonomy
money-map tax salary
money-map search "процент"

money-map render ascii
money-map render md
money-map render dot
money-map export all
```

### PowerShell (Windows)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .

money-map validate
money-map axes
money-map cells
money-map cell A1
money-map taxonomy
money-map tax salary
money-map search "процент"

money-map render ascii
money-map render md
money-map render dot
money-map export all
```

## GUI Quickstart

Установите дополнительные зависимости и запустите графический интерфейс:

```bash
pip install -e ".[ui]"
money-map ui
```

Альтернатива без CLI:

```bash
python -m streamlit run .\\src\\money_map\\ui\\app.py
```

## Что умеет CLI

- `money-map validate` — проверка данных YAML и ссылочной целостности.
- `money-map axes` — вывод осей.
- `money-map cells` — список всех ячеек 2×2×2.
- `money-map cell A1` — детали ячейки.
- `money-map taxonomy` — список механизмов дохода.
- `money-map tax <id>` — детали механизма.
- `money-map bridges [--from A1] [--to A2]` — список мостов.
- `money-map paths` — список типовых маршрутов.
- `money-map path <id>` — детали маршрута.
- `money-map search "<text>"` — поиск по описаниям.
- `money-map classify --sell result --to platform --value percent` — классификация по тегам.
- `money-map classify "text..."` — классификация по тексту.
- `money-map graph show|shortest|outgoing` — работа с графом переходов.
- `money-map render ascii|md|dot` — рендеринг.
- `money-map export all` — построение экспорта в `exports/`.
- `money-map ui` — запуск графического интерфейса на Streamlit.

## Структура данных

Все данные находятся в `data/` и загружаются из YAML. Можно переопределить путь через
переменную окружения `MONEY_MAP_DATA_DIR`.

## Экспорт

Команда `money-map export all` создаёт:

- `exports/matrix.md`
- `exports/bridges.md`
- `exports/paths.md`
- `exports/taxonomy.md`
- `exports/full_summary.md`
- `exports/map_ascii.txt`
- `exports/graph.dot`
- `exports/index.json`
