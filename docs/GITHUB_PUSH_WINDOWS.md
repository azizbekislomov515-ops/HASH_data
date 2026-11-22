# HASH_data (HashForge) loyihasini GitHub'ga push qilish — Windows uchun to'liq qo'llanma

## 0. Kerakli narsalar

| Nima | Qayerdan |
|------|----------|
| GitHub akkaunt | https://github.com/signup |
| Git for Windows | https://git-scm.com/download/win |
| (ixtiyoriy) GitHub CLI | https://cli.github.com |

---

## 1. Git'ni o'rnatish

1. https://git-scm.com/download/win dan **64-bit Git for Windows Setup** ni yuklab oling.
2. O'rnatishda hammasini default qoldiring, faqat quyidagilarga e'tibor bering:
   - **Default editor** → `Notepad` yoki `Visual Studio Code` ni tanlang (Vim emas).
   - **Initial branch name** → `Override ... ` → `main` deb yozing.
   - **PATH** → `Git from the command line and also from 3rd-party software` (tavsiya etilgan).
   - **Line ending** → `Checkout Windows-style, commit Unix-style line endings`.
   - **Credential helper** → `Git Credential Manager` (login uchun kerak).
3. **PowerShell** yoki **Git Bash** ni oching va tekshiring:

```powershell
git --version
```

`git version 2.x.x` chiqsa — tayyor.

---

## 2. Git'ga ismingiz va emailingizni kiritish (bir marta)

```powershell
git config --global user.name "Ismingiz"
git config --global user.email "github-dagi-emailingiz@example.com"
git config --global init.defaultBranch main
```

> Email GitHub akkauntingizdagi email bilan bir xil bo'lsin, aks holda commitlar profilingizga bog'lanmaydi.
> Emailni yashirmoqchi bo'lsangiz: GitHub → Settings → Emails → `ID+username@users.noreply.github.com` dan foydalaning.

---

## 3. GitHub'da bo'sh repository yaratish

1. https://github.com/new ga kiring.
2. **Repository name**: `HASH_data` (yoki `hashforge`).
3. **Public** yoki **Private** — o'zingiz tanlang.
4. ⚠️ **README, .gitignore, license qo'shmang** — hammasi bo'sh qolsin (loyihada ular allaqachon bor, aks holda push'da konflikt bo'ladi).
5. **Create repository** ni bosing.
6. Ochilgan sahifadan URL ni nusxalang:
   `https://github.com/USERNAME/HASH_data.git`

---

## 4. Loyiha papkasiga kirish

Loyihani Windows'ga ko'chiring (masalan `C:\Projects\HASH_data`), keyin:

```powershell
cd C:\Projects\HASH_data
```

> Maslahat: Explorer'da papkani oching → manzil qatoriga `powershell` yozib Enter bosing — terminal shu papkada ochiladi.

⚠️ Agar loyihani Linux'dan nusxalayotgan bo'lsangiz, `build\`, `dist\`, `build-linux*\`, `dist-linux*\`, `__pycache__\`, `.pytest_cache\` papkalarini ko'chirmasangiz ham bo'ladi (≈450 MB) — ular baribir `.gitignore` orqali e'tiborsiz qoldiriladi.

---

## 5. Git repository'ni ishga tushirish va birinchi commit

```powershell
git init
git add .
git status
```

`git status` chiqishini tekshiring. Ro'yxatda **bo'lmasligi kerak**:
`build/`, `dist/`, `__pycache__/`, `.venv/`, `.pytest_cache/`, `*.pyc`.

Ro'yxatda **bo'lishi kerak**:
`hashforge/`, `tests/`, `tools/`, `assets/`, `docs/`, `.github/`, `main.py`, `README.md`,
`requirements.txt`, `requirements-dev.txt`, `pytest.ini`, `hashforge.spec`, `build.bat`, `build.sh`,
`.gitignore`, `.gitattributes`.

Hammasi to'g'ri bo'lsa:

```powershell
git commit -m "Initial commit: HashForge hash calculator"
```

---

## 6. GitHub'ga ulash va push qilish

```powershell
git branch -M main
git remote add origin https://github.com/USERNAME/HASH_data.git
git push -u origin main
```

`USERNAME` o'rniga GitHub foydalanuvchi nomingizni yozing.

### Login oynasi chiqadi
Birinchi push'da **Git Credential Manager** oynasi ochiladi:
- **Sign in with your browser** ni bosing → brauzerda GitHub'ga kiring → **Authorize** ni bosing.
- Login Windows'da saqlanadi, keyingi safar so'ramaydi.

> GitHub endi oddiy parolni qabul qilmaydi. Agar terminal parol so'rasa, parol o'rniga **Personal Access Token** kiriting (8-bo'limga qarang).

Push tugagach, `https://github.com/USERNAME/HASH_data` sahifasini yangilang — fayllar ko'rinadi.

---

## 7. GitHub Actions (avtomatik build)

Loyihada `.github/workflows/build-windows.yml` bor. Push'dan keyin:

1. Repo sahifasida **Actions** tabini oching.
2. `Cross-platform tests and Windows build` ishlayotganini ko'rasiz (Linux + Windows testlari, keyin Windows `.exe` build).
3. Tugagach, run ichidagi **Artifacts** bo'limidan tayyor Windows build'ni yuklab olish mumkin.
4. `onefile` rejimida build qilish: **Actions** → workflow'ni tanlang → **Run workflow** → `mode: onefile`.

---

## 8. Muammolar va yechimlar

| Xato | Sabab / Yechim |
|------|----------------|
| `'git' is not recognized...` | Git o'rnatilmagan yoki PATH'da yo'q. Git'ni qayta o'rnating, terminalni yoping-oching. |
| `remote origin already exists` | `git remote set-url origin https://github.com/USERNAME/HASH_data.git` |
| `failed to push some refs` / `rejected (fetch first)` | GitHub'da repo README bilan yaratilgan. Yechim: `git pull origin main --allow-unrelated-histories`, keyin `git push -u origin main`. |
| `Support for password authentication was removed` | Parol o'rniga token kerak: GitHub → Settings → Developer settings → **Personal access tokens → Tokens (classic)** → Generate → `repo` belgilang → tokenni parol o'rniga kiriting. |
| `Permission denied (403)` | Boshqa akkaunt saqlanib qolgan. **Control Panel → Credential Manager → Windows Credentials** → `git:https://github.com` ni o'chiring va qayta push qiling. |
| `LF will be replaced by CRLF` ogohlantirishi | Zararsiz. `.gitattributes` qator oxirlarini avtomatik boshqaradi. |
| `File ... exceeds GitHub's file size limit of 100 MB` | `build/` yoki `dist/` commit'ga tushib qolgan. `git rm -r --cached build dist` → `git commit -m "Remove build artifacts"` → qayta push. |
| `Filename too long` | `git config --global core.longpaths true` |

---

## 9. Keyingi o'zgarishlarni push qilish (har kungi ish)

```powershell
git status                       # nima o'zgardi
git add .                        # hammasini tayyorlash
git commit -m "Nima qilganingiz haqida qisqa izoh"
git push                         # GitHub'ga yuborish
```

Boshqa kompyuterdan o'zgarishlarni olish:

```powershell
git pull
```

Loyihani yangi Windows PC'ga yuklab olish:

```powershell
git clone https://github.com/USERNAME/HASH_data.git
cd HASH_data
py -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python -m pytest
python main.py
```

> PowerShell `activate` ni bloklasa: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` → `Y`.

---

## 10. (Ixtiyoriy) GitHub CLI bilan tezkor usul

3–6-bo'limlarni bitta buyruq bilan bajarish:

```powershell
winget install --id GitHub.cli
gh auth login                    # GitHub.com → HTTPS → Login with a web browser
cd C:\Projects\HASH_data
git init
git add .
git commit -m "Initial commit: HashForge hash calculator"
gh repo create HASH_data --private --source=. --push
```

(`--private` o'rniga `--public` yozish mumkin.)
