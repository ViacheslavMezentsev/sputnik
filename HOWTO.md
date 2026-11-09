# Памятка: частые команды и проблемы

Сюда заглядывают разработчик и агент, когда что-то не работает, прежде чем искать новое
решение. Для каждой проблемы указано, как её исправить и как вернуть прежнее состояние.

Условные обозначения: **PS** — PowerShell на Windows, **sh** — оболочка Linux или WSL.
Команды git одинаковы в обеих, кроме кавычек (раздел «Псевдоним `git land`»).

## Подмодули

```sh
git clone --recursive https://github.com/ViacheslavMezentsev/sputnik.git
git submodule update --init                 # если клонировали без --recursive
git submodule status                        # закреплённые коммиты
```

Сменить закреплённый коммит подмодуля (отдельной задачей, ТЗ п. 10.5):

```sh
git -C modules/stm32-cmake-yml fetch --tags
git -C modules/stm32-cmake-yml checkout v0.10.3     # нужный тег или коммит
git add modules/stm32-cmake-yml
git commit -m "build(modules): stm32-cmake-yml 0.10.3"
```

stm32-cmake закреплён на коммите, проверенном в CI stm32-cmake-yml (`ci/dependencies.lock.json`
этого модуля): при обновлении stm32-cmake-yml сверяйте его с закреплённым здесь.

| Проблема | Решение |
| --- | --- |
| Папка подмодуля пустая | `git submodule update --init` |
| `git status` показывает `modified: modules/… (new commits)` | Подмодуль переключили случайно: `git submodule update` вернёт закреплённый коммит |

## Проверка ТЗ

```sh
python3 skills/embedded-tech-spec/scripts/check_spec.py --strict docs/TECHNICAL_SPECIFICATION.md
```

Скрипт ловит повторы номеров, ссылки на несуществующие пункты, тест-кейсы вне матрицы,
пункты без маркера и несогласованные ревизии. Смысл требований он не проверяет.

## Git: рабочий цикл без PR

### Последовательность работы

Ветка `<агент>/<задача>` создаётся от свежего main и после проверок сливается в main
перемоткой (fast-forward). Слить без PR в веб-интерфейсе GitHub нельзя, и автоудаление веток
GitHub работает только для PR, поэтому слияние и уборка делаются локально.

```
git switch main
git pull --ff-only
git switch -c claude/<задача>          # новая ветка
# … коммиты …
git push -u origin claude/<задача>     # дождаться зелёного CI
git land claude/<задача>               # перемотать main, отправить, удалить ветку
```

Пока в репозитории нет CI, «дождаться CI» означает проверить ветку локально (сборка, тесты,
`check_spec.py`). Перемотка не создаёт merge-коммит: в main попадают те же подписанные
коммиты, и GitHub показывает их Verified. Если ветка отстала от main, `git land`
остановится на `--ff-only`, ничего не изменив. Тогда ветку переносят на свежий main и снова
подписывают:

```
git switch claude/<задача>
git rebase -S origin/main              # конфликты: исправить, git add, git rebase --continue
git push --force-with-lease            # только для своей неслитой ветки
```

Force push в main и в чужие ветки запрещён.

### Ветка агента из клона `../.work`

Агент не коммитит в рабочую копию владельца. Рядом с репозиториями лежит скрытая папка
`.work`: в ней ключ подписи агента (общий) и отдельный клон для каждого репозитория. Папка
вне репозиториев, поэтому в `.gitignore` её не добавляют; в облачную синхронизацию её не кладут.

```text
<папка с репозиториями>\
  .work\
    keys\claude_signing, claude_signing.pub, allowed_signers
    sputnik\                                  # клон агента (HTTPS, push отключён)
  sputnik\                                    # рабочая копия владельца
```

Открытый ключ `claude_signing.pub` добавлен в GitHub как **Signing Key** (не Authentication
Key): им нельзя выполнить push. В клоне агента подпись включена локально (`commit.gpgsign`,
`gpg.format ssh`, `user.signingkey`), committer — владелец с подтверждённым в GitHub email,
участие агента отмечается строкой `Co-Authored-By`.

Владелец принимает ветку из корня своего репозитория (PS или sh):

```
git fetch ../.work/sputnik claude/<задача>:claude/<задача>
git -c gpg.ssh.allowedSignersFile=../.work/keys/allowed_signers log --show-signature --oneline main..claude/<задача>
git push -u origin claude/<задача>     # дождаться CI
git land claude/<задача>
```

Каждый коммит в выводе `log --show-signature` должен иметь строку `Good "git" signature for
<email> with ED25519 key …`. Относительный путь `../.work` работает только из копии, рядом
с которой лежит `.work`. Из WSL копия на диске Windows видна как `/mnt/d/…`; там путь
указывают полностью.

`fetch` переносит коммиты без изменений, вместе с подписями. Ветку с тем же именем в своей
копии перед повторным приёмом обновляют тем же `fetch` (только перемотка; при расхождении —
`+claude/<задача>:claude/<задача>`, если своих коммитов в ней нет). После `git land` агент
синхронизирует клон: `git fetch origin && git switch main && git merge --ff-only origin/main
&& git branch -d claude/<задача>`.

| Проблема | Решение |
| --- | --- |
| `'../.work/…' does not appear to be a git repository` | Команда запущена не из той копии: `pwd`, затем полный путь к клону |
| `detected dubious ownership in repository` (WSL, диск Windows) | `git config --global --add safe.directory <полный путь к клону>` |
| `gpg.ssh.allowedSignersFile needs to be configured` | Передать файл: `-c gpg.ssh.allowedSignersFile=../.work/keys/allowed_signers`; это не значит, что подписи нет |
| `No signature` у коммита ветки | Коммит сделан без подписи: агент пересоздаёт ветку с `git rebase -S` в своём клоне, владелец забирает её заново с `+` |

Вернуть: удалить принятую ветку — `git branch -D claude/<задача>`; отключить ключ агента —
удалить его в GitHub; убрать клон — удалить папку `.work\sputnik`.

### Псевдоним `git land`

Установка — одинарные кавычки обязательны: в PowerShell внутри двойных кавычек `$`
подставляется самим PowerShell.

```powershell
git config --global --unset-all alias.land   # если уже был; ошибка «no such section» не страшна
git config --global alias.land '!f() { b=${1:-$(git branch --show-current)}; git fetch origin && git switch main && git merge --ff-only origin/main && git merge --ff-only $b && git push --atomic origin main :$b && git branch -d $b; }; f'
git config --global --get-all alias.land     # ровно одна строка с b=${1:-$(git branch --show-current)}
```

Что делает `git land <ветка>`: `fetch` → перемотка main до `origin/main` → перемотка main до
ветки → одним атомарным push отправка main и удаление ветки на GitHub → удаление локальной
ветки.

| Проблема | Решение |
| --- | --- |
| `syntax error: unexpected end of file`, в ошибке `b=;` | Псевдоним записан в двойных кавычках из PowerShell: удалить (`--unset-all`) и записать заново в одинарных |
| `fatal: Not possible to fast-forward` | Ветка отстала от main: `git rebase -S origin/main` (выше) |
| Push отклонён: protected branch, required pull request | В Settings → Rules снять требование PR для main или разрешить себе обход (bypass) |

### Как вернуть состояние

| Ситуация | Команда |
| --- | --- |
| Отменить незакоммиченные правки в файлах | `git restore <файл>` или `git restore .` |
| Отменить последний неотправленный коммит, сохранив правки | `git reset --soft HEAD~1` |
| Локальный main испорчен, но ещё не отправлен | `git switch main && git reset --hard origin/main` |
| Удалили ветку по ошибке | `git reflog` → найти хэш → `git branch <ветка> <хэш>` |
| Отменить коммит, уже отправленный в main | `git revert <хэш>` новым подписанным коммитом; историю main не переписывать |
| Прервать неудачный rebase или merge | `git rebase --abort` / `git merge --abort` |

### Концы строк

- На Windows обычно `core.autocrlf=true`: в рабочей копии CRLF, в репозитории LF. Файлы
  `.github/**`, `*.sh`, `*.S`, `*.ioc` всегда LF (`.gitattributes`).
- Все файлы показаны изменёнными без реальной правки — концы строк: после правки
  `.gitattributes` выполнить `git add --renormalize .`.
- `fatal: Unable to create '…/.git/index.lock': File exists` — убедиться, что git не запущен
  (IDE, другой терминал), затем удалить `.git/index.lock`.
