# Спутник

Прототип наручного навигатора с небольшим экраном: запись трека в GPX, отображение трека на
растровой карте JNX (Garmin BirdsEye), навигация по GPS/ГЛОНАСС, анализ трека во время записи
и после сохранения.

Отдельный режим обмена с ПК: плата подключается по USB как сетевое устройство (RNDIS), в
браузере можно смотреть карты и треки с карты памяти, загружать, скачивать и удалять файлы
JNX и GPX.

Состояние: [техническое задание](docs/TECHNICAL_SPECIFICATION.md) ревизии 1.1, выбраны модули
отладочного стенда и распределены выводы ([подключение](docs/WIRING.md)). Кода и проектов
CubeMX пока нет.

```mermaid
flowchart LR
    G["Приёмник GNSS<br/>NMEA"] --> L["Бизнес-логика<br/>(без зависимости от платы)"]
    SD["microSD<br/>JNX, GPX"] <--> L
    K["Кнопки"] --> L
    L --> D["Экран"]
    L <--> B["Слой платы<br/>F411CE | H723VG"]
```

## Платы

| Профиль | Плата | MCU | Flash / RAM |
| :--- | :--- | :--- | :---: |
| `F411CE` | [WeAct BlackPill](https://github.com/WeActStudio/WeActStudio.MiniSTM32F4x1) V3.1 | STM32F411CEU6 | 512 / 128 КиБ |
| `H723VG` | [WeAct STM32H723 Core Board](https://github.com/WeActStudio/WeActStudio.MiniSTM32H723) | STM32H723VGT6 | 1024 / 564 КиБ |

Функции, которые не помещаются в ресурсы F411 (поворот карты по курсу, кадровый буфер, кэш
тайлов, длинные маршруты), доступны только на H723 — таблица в п. 3.3 ТЗ.

| Узел стенда | F411CE | H723VG |
| :--- | :--- | :--- |
| Экран | модуль IPS 240×240, SPI1 + DMA | встроенный ST7735 160×80, SPI4 + DMA |
| Карта памяти | модуль Catalex, SPI2 + DMA | встроенный слот, SDMMC1 4 бит |
| Приёмник | GY-GPS6MV2 (u-blox NEO-6M, только GPS), USART2 | тот же модуль, USART2 |
| Управление | кнопка KEY и светодиод платы | кнопка K1 и светодиод платы |
| Режим обмена | USB RNDIS (USB_OTG_FS) | USB RNDIS (USB_OTG_HS, FS PHY) |

Экран и кнопки наручного варианта, приёмник с ГЛОНАСС и питание пока не выбраны — открытые
вопросы ТЗ.

## Получение

```sh
git clone --recursive https://github.com/ViacheslavMezentsev/sputnik.git
cd sputnik
git submodule update --init      # если клонировали без --recursive
```

Сборки пока нет: она появится вместе с проектами CubeMX. Планируется CMake с
[stm32-cmake](https://github.com/ObKo/stm32-cmake) и
[stm32-cmake-yml](https://github.com/ViacheslavMezentsev/stm32-cmake-yml), профиль платы
выбирается пресетом (`STM32_YML_PROFILE`).

## Структура

```text
boards/         профили плат для stm32-cmake-yml (TOML); позже — проекты CubeMX и слой платы
docs/           техническое задание
modules/        git-подмодули: stm32-cmake, stm32-cmake-yml, stm32-gdbtest
skills/         копии навыков агентов из demo-stm32-skills (не правятся здесь)
```

Планируется: `src/` — бизнес-логика, `hil/` — DDTT-сценарии для плат, `tests/` — тесты на ПК
и маленькие тестовые файлы, `ci/` — проверки.

| Подмодуль | Версия | Коммит |
| :--- | :--- | :--- |
| [stm32-cmake](https://github.com/ObKo/stm32-cmake) | v2.1.0+ | `ecc5acc` (закреплён в CI stm32-cmake-yml 0.10.2) |
| [stm32-cmake-yml](https://github.com/ViacheslavMezentsev/stm32-cmake-yml) | 0.10.2 | `3333d0b` |
| [stm32-gdbtest](https://github.com/ViacheslavMezentsev/stm32-gdbtest) | 0.6.1 | `7f4f2ef` |

## Сторонние компоненты

| Компонент | Назначение | Лицензия |
| :--- | :--- | :--- |
| [TJpgDec](https://elm-chan.org/fsw/tjpgd/00index.html) R0.03 (ChaN) | декодирование JPEG-тайлов JNX | BSD-подобная (ChaN) |

Добавляются по мере появления кода (ТЗ, п. 9.7.2, 9.7.4): сетевой стек режима обмена переносится
из проекта mcu_gcs_web_board (FreeRTOS, FreeRTOS-Plus-TCP, RNDIS).

## Формат JNX

Чтение JNX пишется по описанию формата
([рус.](https://web.archive.org/web/20220929144544/http://whiter.brinkster.net/JNX.shtml),
[англ.](https://web.archive.org/web/20151023153145/http://whiter.brinkster.net/en/JNX.shtml)).
Исходники [GPXSee](https://github.com/tumic0/GPXSee) (GPL-3.0) используются только для понимания
формата; код из них не копируется. Подробности — раздел 5 и приложение E ТЗ.

## Документы

- [Техническое задание](docs/TECHNICAL_SPECIFICATION.md)
- [Подключение модулей стенда](docs/WIRING.md)
- [TODO](TODO.md) — текущее состояние и ближайшие шаги
- [CHANGELOG](CHANGELOG.md) — изменения
- [AGENTS](AGENTS.md) — правила для участников и агентов
- [HOWTO](HOWTO.md) — команды Git и частые проблемы
- [Навыки агентов](skills/README.md)

## Лицензия

MIT ([LICENSE](LICENSE)). Подмодули и копии навыков — со своими лицензиями (MIT у модулей автора
и навыков; stm32-cmake — MIT).
