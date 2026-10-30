# Subtitle Forge

Subtitle Forge превращает JSON-транскрипт с временными метками в ASS-субтитры с оформлением. При необходимости он может получить такой транскрипт из видео через уже настроенный локальный faster-whisper и прожечь ASS в копию видео через FFmpeg/libass.

## Как устроена обработка

```text
JSON или SRT ── parsing.py ──> Transcript / Segment / Word
                                      │
                    встроенный стиль или Python-плагин
                                      │
                              список Event
                                      │
                                  ass.py ──> .ass
                                                │ опционально
                                             ffmpeg ──> видео с субтитрами

видео ── transcribe.py ──> существующий ~/whisper-venv ──> транскрипт JSON
```

`models.py` задаёт и проверяет модель данных. `parsing.py` читает JSON и SRT. Стиль преобразует модель в события показа; `ass.py` записывает их в ASS вместе с разрешением кадра и настройками шрифта. Для прожига `video.py` запускает FFmpeg с фильтром `ass` и кодирует новое видео в H.264, копируя аудио без перекодирования. Генерация ASS сама по себе не требует внешних Python-пакетов.

## Быстрый старт

Нужен Python 3.10+. Самый простой пример использует уже включённый файл `examples/transcript.json`:

```sh
git clone https://github.com/Nick1t0s/subtitle-forge.git
cd subtitle-forge
python3 -m subtitle_forge styles
python3 -m subtitle_forge generate examples/transcript.json \
  -o /tmp/subtitle-forge-example.ass --style karaoke
```

Установка проекта не обязательна: команды `python -m subtitle_forge` работают из корня репозитория. Чтобы установить CLI-команду `subtitle-forge` в отдельное окружение, создайте venv и установите проект из корня:

```sh
python3 -m venv /tmp/codex-venv-subtitle-forge
/tmp/codex-venv-subtitle-forge/bin/pip install -e .
/tmp/codex-venv-subtitle-forge/bin/subtitle-forge styles
```

Не устанавливайте пакеты в системный Python. Subtitle Forge не требует сторонних Python-зависимостей для чтения, генерации ASS или прожига видео.

## Сквозной пример: YouTube-видео до готового MP4

Для этого сценария нужны `yt-dlp`, настроенное окружение `~/whisper-venv` с faster-whisper и локальной моделью, а также FFmpeg с фильтром `libass`. Установите `yt-dlp` своим обычным способом, если его ещё нет. Возьмите короткий публичный ролик, который разрешено скачивать и обрабатывать, и подставьте его URL вместо `YOUTUBE_URL`:

```sh
mkdir -p demo-youtube
yt-dlp --no-playlist -f "bv*+ba/b" --merge-output-format mp4 \
  -o 'demo-youtube/source.%(ext)s' 'YOUTUBE_URL'
```

Здесь `demo-youtube/` — локальная рабочая папка, а не каталог для распространения ролика. Распознайте речь. `transcribe` всегда вызывает именно `~/whisper-venv/bin/python`; оно не устанавливает туда пакеты и не скачивает модель:

```sh
python3 -m subtitle_forge transcribe demo-youtube/source.mp4 \
  -o demo-youtube/transcript.json --language ru
```

Передайте транскрипт генератору, а затем прожгите субтитры в отдельный файл:

```sh
python3 -m subtitle_forge generate demo-youtube/transcript.json \
  -o demo-youtube/subtitles.ass --style karaoke \
  --burn demo-youtube/source.mp4 --video-output demo-youtube/subtitled.mp4
```

Посмотреть фактическое разрешение входного видео можно через `ffprobe`:

```sh
ffprobe -v error -select_streams v:0 \
  -show_entries stream=width,height -of csv=s=x:p=0 demo-youtube/source.mp4
```

Без `--width` и `--height` ASS получает координатное разрешение 1920×1080. Если исходник имеет другой размер или пропорции, укажите его ширину и высоту при генерации: `--width 1080 --height 1920` для вертикального кадра 1080×1920, например. Это задаёт координаты и масштабирование стиля ASS относительно кадра; размер шрифта задаётся в тех же координатах, поэтому вертикальным или низкоразрешённым видео может потребоваться свой `--font-size` и `--margin-v`. При прожиге FFmpeg применяет ASS-фильтр к видео, не меняя его размеры намеренно.

Полный отчёт о фактическом запуске на YouTube-видео, с параметрами и проверкой полученного файла, находится в [docs/youtube-smoke-test.md](docs/youtube-smoke-test.md).

## Транскрипты

JSON содержит массив `segments`. У сегмента обязательны `start`, `end` (секунды) и `text`; поле `words` необязательно. У слова обязательны `start`, `end` и `word` либо `text`. Поле `language` необязательно:

```json
{
  "language": "ru",
  "segments": [
    {
      "start": 0.4,
      "end": 2.1,
      "text": "Привет, мир!",
      "words": [
        {"start": 0.4, "end": 1.0, "word": "Привет,"},
        {"start": 1.1, "end": 2.1, "text": "мир!"}
      ]
    }
  ]
}
```

Все времена должны быть конечными неотрицательными числами, а `end` — строго больше `start`. Слова в сегменте должны идти по времени и не перекрываться. Для стилей, которым нужны слова, задайте у каждого сегмента непустой список `words` с временными метками: программа не пытается вывести время слов из текста.

Можно также подать файл `.srt`. Каждый SRT cue становится одним сегментом с временем всей реплики и без времён слов. Поэтому SRT поддерживает только `classic`; стили `word`, `karaoke`, `typewriter` и `pop` требуют word-level метки. Формат выбирается по расширению `.json` или `.srt`.

## Стили и читаемость

Доступные имена можно получить командой `python -m subtitle_forge styles`.

| Стиль | Поведение | Размер по умолчанию |
| --- | --- | ---: |
| `classic` | Обычные фразы с переносами строк, сохраняет исходное время всей реплики. Поддерживает SRT. | 54 |
| `word` | Одно слово на экране в интервале его метки. | 66 |
| `karaoke` | Показывает фразу и подсвечивает текущее слово; вне интервалов слов текста нет. | 54 |
| `typewriter` | Постепенно добавляет слова по мере их появления. | 52 |
| `pop` | Показывает слова с коротким эффектом появления и увеличения. | 68 |

Размер шрифта не является универсальным числом в пикселях: он задаётся в координатах `PlayRes` ASS. Стандартное разрешение проекта — 1920×1080. Для 1080×1920 полезно начать, например, с `--width 1080 --height 1920 --font-size 54`, затем посмотреть результат на целевом видео. Слишком мелкий текст увеличивают `--font-size`, близость к нижнему краю исправляют `--margin-v`. Для русского текста выбирайте установленный шрифт с кириллицей, например `--font 'DejaVu Sans'`.

Основные параметры генерации:

```text
python -m subtitle_forge generate INPUT -o OUTPUT
  [--style NAME_OR_TRUSTED_PY_FILE]
  [--width N] [--height N] [--font NAME] [--font-size N] [--margin-v N]
  [--burn VIDEO --video-output OUTPUT_VIDEO] [--overwrite]
```

`--burn` и `--video-output` задаются вместе. Если ASS или видео-выход уже существует, команда завершится ошибкой; используйте `--overwrite`, чтобы заменить выходной файл. Входной транскрипт, ASS и видео должны иметь разные пути.

## Распознавание речи

Команда:

```sh
python -m subtitle_forge transcribe VIDEO -o transcript.json [--language ru] [--overwrite]
```

Она запускает `~/whisper-venv/bin/python` и `whisper_worker.py`. Worker использует `WhisperModel("large-v3-turbo", device="cuda", compute_type="float16", local_files_only=True)` и включает `word_timestamps=True`. Следовательно, окружение, CUDA, faster-whisper и файлы модели должны быть готовы заранее. Модель не будет загружаться из сети. При пропуске `--language` язык определяет Whisper.

## Пользовательские стили

В `--style` можно передать путь к доверенному Python-файлу. Модуль стиля должен объявлять:

- `NAME: str` и `DESCRIPTION: str`;
- `CONFIG`: исходный объект `StyleConfig`;
- `REQUIRES_WORDS: bool`;
- `generate(transcript, config)`, возвращающую итерируемую последовательность `Event`.

CLI создаёт конфигурацию через `dataclasses.replace(style.CONFIG, **options)`: только переданные `--font`, `--font-size` и `--margin-v` заменяют поля, остальные поля стиля сохраняются. `generate` отвечает за правильные интервалы и подготовку текста. Обычный текст транскрипта обязательно пропускайте через `escape_text`: ASS использует обратную косую черту и фигурные скобки как управляющую разметку.

```python
from subtitle_forge.ass import Event, StyleConfig, escape_text

NAME = "my_style"
DESCRIPTION = "Одна реплика на событие"
CONFIG = StyleConfig()
REQUIRES_WORDS = False

def generate(transcript, config):
    return [
        Event(segment.start, segment.end, escape_text(segment.text))
        for segment in transcript.segments
    ]
```

Плагины исполняются как Python-код с правами пользователя, поэтому загружайте только доверенные файлы. Чтобы сделать перенос строки/эффект ASS, плагин может сформировать ASS-теги сам, но тогда отвечает за их корректность; экранируйте пользовательский текст отдельно. ASS хранит время с точностью до сотой секунды, поэтому границы округляются до ближайшей сотой. Интервалы, которые после округления стали нулевыми, пропускаются.

## Частые ошибки

- **`Output already exists`** — выберите другой путь либо добавьте `--overwrite`.
- **`--burn and --video-output must be used together`** — укажите оба параметра прожига или уберите оба.
- **`ffmpeg with libass is required`** — установите FFmpeg-сборку с фильтром libass и проверьте `ffmpeg -filters`.
- **`Transcription requires the existing ~/whisper-venv environment`** — проверьте наличие `~/whisper-venv/bin/python`; Subtitle Forge не создаёт и не меняет это окружение.
- **Ошибка CUDA или отсутствует локальная модель** — проверьте faster-whisper, CUDA и наличие `large-v3-turbo` в существующем окружении. Worker работает офлайн и требует CUDA float16.
- **Стиль сообщает, что нужны слова** — JSON должен содержать корректные word timestamps; SRT не содержит таких меток, используйте `classic` или подготовьте JSON с `words`.
- **Субтитров нет или они почти не видны** — проверьте диапазоны времени транскрипта и соответствие `--width`/`--height` реальному разрешению и пропорциям кадра.
- **Текст мелкий, обрезан или не помещается** — подстройте `--font-size` и `--margin-v`; проверьте, что выбранный шрифт установлен и поддерживает нужные символы.
- **JSON не читается** — проверьте корректность JSON, расширение `.json`, обязательные поля и порядок непересекающихся меток слов.

## Тесты

Чтобы запустить набор тестов репозитория:

```sh
python -m unittest discover -s tests -v
```
