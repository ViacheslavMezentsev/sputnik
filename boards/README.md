# Профили плат

| Профиль | Плата | MCU | Flash / RAM | Файл |
| :--- | :--- | :--- | :---: | :--- |
| `F411CE` | [WeAct BlackPill](https://github.com/WeActStudio/WeActStudio.MiniSTM32F4x1) V3.1 | STM32F411CEU6 | 512 / 128 КиБ | [F411CE.toml](F411CE.toml) |
| `H723VG` | [WeAct STM32H723 Core Board](https://github.com/WeActStudio/WeActStudio.MiniSTM32H723) | STM32H723VGT6 | 1024 / 564 КиБ | [H723VG.toml](H723VG.toml) |

Профиль — файл именованного профиля stm32-cmake-yml (TOML): MCU, пакет Cube, позже — `.ioc`,
скрипт компоновщика и исходники платы. Бизнес-логика от платы не зависит и в профили не входит.

Планируемая раскладка (появится на следующих этапах):

```text
boards/
  F411CE.toml            профиль сборки
  F411CE/                проект CubeMX (.ioc), сгенерированный Core/, адаптер платы
  H723VG.toml
  H723VG/
```

Сейчас это заготовки: Configure с ними не проверялся.
