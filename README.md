# Subtitle Forge

Subtitle Forge превращает транскрипт в оформленные субтитры ASS. Он также умеет распознавать речь в видео через уже настроенное локальное окружение faster-whisper.

## Быстрый старт

Нужен Python 3.10 или новее. Создайте виртуальное окружение и установите проект в режиме разработки:

```sh
python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
python -m pip install -e .
```

Посмотреть доступные стили и создать файл ASS:

```sh
python -m subtitle_forge styles
python -m subtitle_forge generate transcript.json -o subtitles.ass --style karaoke
```

Создание ASS-файла использует только стандартную библиотеку Python. Чтобы сразу встроить субтитры в видео, нужен FFmpeg с фильтром `libass`:

```sh
python -m subtitle_forge generate transcript.json -o subtitles.ass --style classic \
  --burn input.mp4 --video-output subtitled.mp4
```

FFmpeg нужен только для `--burn`. Параметры `--burn` и `--video-output` указываются вместе. Существующие файлы защищены от перезаписи; для замены добавьте `--overwrite`.

## Формат транскрипта

JSON содержит язык (необязательное поле `language`) и массив `segments`. Для каждого сегмента нужны `start`, `end` в секундах и текст `text`. Массив `words` необязателен; его элементы содержат времена и текст слова в поле `word` либо `text`:

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

Времена должны быть конечными неотрицательными числами, а `end` — больше `start`. Также можно подавать SRT. В нём указано время всей реплики, поэтому программа не выдумывает время отдельных слов. Только стиль `classic` работает с SRT; стили `word`, `karaoke`, `typewriter` и `pop` требуют массива `words` с временными метками.

## Стили

Выберите стиль аргументом `--style`:

| Стиль | Что показывает | Размер шрифта по умолчанию |
| --- | --- | ---: |
| `classic` | Фразу целиком, разбивает длинный текст на читаемые части; для SRT сохраняет время реплики | 54 |
| `word` | По одному слову только в его интервале времени | 66 |
| `karaoke` | Фразу целиком, подсвечивая слово в его интервале; паузы между словами остаются пустыми | 54 |
| `typewriter` | Постепенно добавляет слова по мере их появления | 52 |
| `pop` | Показывает каждое слово с короткой анимацией увеличения и появления | 68 |

Размеры в таблице — начальные значения стилей. Их можно переопределить через `--font-size`; также доступны `--font`, `--margin-v`, `--width` и `--height`. Размер кадра по умолчанию — 1920×1080, вертикальный отступ — 70. В ASS время хранится с точностью до сотых секунды, поэтому при записи оно округляется до ближайшей сотой. Используйте `python -m subtitle_forge generate --help`, чтобы увидеть параметры команды.

## Распознавание речи

Команда `transcribe` использует только существующее окружение `~/whisper-venv/bin/python`. В нём заранее должны быть установлены faster-whisper и CUDA-зависимости, а модель `large-v3-turbo` должна уже находиться локально. Subtitle Forge не скачивает модели и не устанавливает пакеты в это окружение. Распознавание выполняется через CUDA, в режиме float16, с `word_timestamps=True` и `local_files_only=True`.

```sh
python -m subtitle_forge transcribe input.mp4 -o transcript.json --language ru
```

Описание временных меток слов есть в [документации faster-whisper](https://github.com/SYSTRAN/faster-whisper#word-level-timestamps).

## Пользовательские стили

Вместо встроенного имени `--style` можно передать путь к Python-файлу. Такой файл должен предоставлять `NAME`, `DESCRIPTION`, `CONFIG`, `REQUIRES_WORDS` и функцию `generate(transcript, config)`, возвращающую список событий `Event`.

Файлы стилей выполняются как Python-код с правами текущего пользователя. Загружайте только доверенные плагины. Экранируйте текст транскрипта функцией `escape_text` перед созданием ASS-событий, чтобы содержимое реплик не интерпретировалось как разметка ASS:

```python
from subtitle_forge.ass import Event, StyleConfig, escape_text

NAME = "my_style"
DESCRIPTION = "Простой пользовательский стиль"
CONFIG = StyleConfig()
REQUIRES_WORDS = False

def generate(transcript, config):
    return [
        Event(segment.start, segment.end, escape_text(segment.text))
        for segment in transcript.segments
    ]
```

## Тесты

Запустите тесты из корня репозитория:

```sh
python -m unittest discover -s tests -v
```
