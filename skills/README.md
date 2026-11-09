# Навыки агентов

Копии навыков из [demo-stm32-skills](https://github.com/ViacheslavMezentsev/demo-stm32-skills),
которые нужны в этом проекте. Навык подключается к агенту способом, который поддерживает
инструмент (например, копированием папки в `.claude/skills/`); для сборки прошивки навыки не нужны.

| Навык | Версия | Для чего в проекте |
| :--- | :---: | :--- |
| [embedded-tech-spec](embedded-tech-spec/SKILL.md) | 0.1 | Ведение ТЗ `docs/TECHNICAL_SPECIFICATION.md`: ревизии, требования, тест-кейсы, матрица |
| [release-spiral](release-spiral/SKILL.md) | 1.0.0 | Документ о ходе выпусков по истории Git, прогонам на стенде и CI |
| [stm32-diag-record](stm32-diag-record/SKILL.md) | 1.10.0 | Запись переменных работающей прошивки (OpenOCD, RTT) в MCAP/bag |
| [stm32-gdbpy-scenario](stm32-gdbpy-scenario/SKILL.md) | 1.5.1 | Сценарии GDB-Python для проверок на плате |
| [stm32-renode-emulator](stm32-renode-emulator/SKILL.md) | 1.2.0 | Прогон прошивки в Renode без платы |
| [weact-logic-analyzer](weact-logic-analyzer/SKILL.md) | 1.4.0 | Измерения логическим анализатором WeAct (SPI экрана, UART приёмника, тайминги) |

## Источник

- Репозиторий: https://github.com/ViacheslavMezentsev/demo-stm32-skills
- Исходный коммит: `8ee9a154711b098924fd9beae03f20be00555d2f` (main, 08.11.2026)
- Лицензия: MIT, Copyright (c) 2023 Viacheslav Mezentsev
  ([текст](https://github.com/ViacheslavMezentsev/demo-stm32-skills/blob/8ee9a154711b098924fd9beae03f20be00555d2f/LICENSE));
  у каждого навыка `license: MIT` в заголовке `SKILL.md`.

## Правила

1. Копии не правятся в этом репозитории. Исправления и доработки вносятся в demo-stm32-skills,
   затем копии обновляются целиком.
2. Обновление: скопировать папки навыков из нужного коммита demo-stm32-skills поверх текущих
   (удалив прежние файлы), записать новый коммит и версии в таблицы выше, отметить обновление
   в `CHANGELOG.md`.
3. Проверка, что копия не изменена (sh, из корня репозитория, рядом лежит клон demo-stm32-skills
   на исходном коммите):

   ```sh
   for s in embedded-tech-spec release-spiral stm32-diag-record stm32-gdbpy-scenario \
            stm32-renode-emulator weact-logic-analyzer; do
     diff -r "skills/$s" "../demo-stm32-skills/$s" || echo "ОТЛИЧАЕТСЯ: $s"
   done
   ```
