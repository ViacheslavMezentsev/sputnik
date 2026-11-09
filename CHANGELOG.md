# Журнал изменений

Формат — [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/), версии — [SemVer](https://semver.org/lang/ru/).

## [Unreleased]

### Изменено

- ТЗ, ревизия 1.1: модули отладочного стенда (экран IPS 240×240, Catalex microSD,
  GY-GPS6MV2 с NEO-6M для F411CE; встроенные экран и слот microSD для H723VG), распределение
  интерфейсов, выводов и DMA, тактирование F411 96 МГц, быстрый вывод на экран (DMA, две полосы,
  кэш H723), декодер TJpgDec, режим обмена с ПК через веб-сервер по USB RNDIS, отладочная
  раскладка одной кнопки; 63 тест-кейса, 34 вопроса.
- Профили `boards/*.toml`: выводы стенда в комментариях.

### Добавлено

- `docs/WIRING.md` — подключение модулей стенда.
- HOWTO: подготовка карт microSD (FAT32, кластер 32 КиБ).
- Структура репозитория: `boards/` с заготовками профилей `F411CE` и `H723VG` (TOML,
  stm32-cmake-yml), `docs/`, `.gitignore`, `.gitattributes`.
- Подмодули в `modules/`: stm32-cmake (`ecc5acc`), stm32-cmake-yml 0.10.2, stm32-gdbtest 0.6.1.
- Копии навыков из demo-stm32-skills (`8ee9a15`) в `skills/`: embedded-tech-spec, release-spiral,
  stm32-diag-record, stm32-gdbpy-scenario, stm32-renode-emulator, weact-logic-analyzer.
- Техническое задание, ревизия 1.0 (черновик для согласования): разделение функций между платами,
  чтение JNX, запись GPX, навигация, анализ трека; 51 тест-кейс, матрица прослеживаемости,
  26 открытых вопросов.
- README, TODO, AGENTS, HOWTO, CHANGELOG.
