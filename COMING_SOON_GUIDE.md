# de luzex — Coming Soon & VIP Launch Notification System

સંપૂર્ણ End-to-End ગાઈડ: કમિંગ સૂન પેજ, સબસ્ક્રાઇબર મેનેજમેન્ટ અને વેબસાઇટ લોન્ચ ઈમેઈલ બ્રોડકાસ્ટ સિસ્ટમ.

---

## 🌟 સિસ્ટમ આર્કિટેક્ચર (System Overview)

1. **Coming Soon Frontend (`index.html`)**
   - **Real-Time API Integration**: જ્યારે યુઝર ઇમેઇલ નાખીને `Notify Me` પર ક્લિક કરે છે ત્યારે સીધો બેકએન્ડ એન્ડપોઇન્ટ `POST http://localhost:8000/api/v1/newsletter/subscribe` પર રિક્વેસ્ટ જાય છે.
   - **Luxury Toast Feedback**:
     - નવું સબસ્ક્રિપ્શન: `✨ Thank you. We will notify you as soon as we launch.`
     - પહેલેથી રજીસ્ટર્ડ હોય તો: `✨ You're already subscribed. We'll notify you once we go live.`
   - **Offline & Fail-Safe Fallback**: જો ઇન્ટરનેટ ધીમું હોય અથવા બેકએન્ડ ઓફલાઇન હોય, તો પણ યુઝરનો ઇમેઇલ બ્રાઉઝરના `localStorage` માં સેવ થઈ જાય છે અને બેકએન્ડ ચાલુ થતાં જ આપમેળે બેકગ્રાઉન્ડમાં સિંક થઈ જાય છે (ઝીરો ડેટા લોસ).

2. **Backend & Database Storage (`deluzex-backend`)**
   - **MongoDB Atlas Storage**: દરેક સબસ્ક્રાઇબર સીધા મોંગોડીબી ક્લાઉડ ક્લસ્ટરમાં `newsletter_subscribers` કલેક્શનમાં સ્ટોર થાય છે:
     - `email`: સબસ્ક્રાઇબરનું ઇમેઇલ
     - `subscribed_at`: સબસ્ક્રાઇબ કર્યાનો સમય (UTC)
     - `is_notified: false` (હજુ લોન્ચ ઈમેલ મોકલાયો નથી)
     - `source: "coming_soon"`
   - **Duplicate Prevention**: એક જ ઇમેઇલ ફરી નાખવાથી ડુપ્લિકેટ એન્ટ્રી થતી નથી.

3. **Launch Email Broadcast Engine (`send_launch_emails.py`)**
   - 1-2 અઠવાડિયા પછી જ્યારે વેબસાઇટ લાઈવ થાય, ત્યારે એક જ કમાન્ડથી બધા પેન્ડિંગ સબસ્ક્રાઇબર્સને લક્ઝરી HTML Launch Announcement Email સેન્ડ થઈ જશે.
   - ઈમેલ સેન્ડ થયા પછી ડેટાબેઝમાં `is_notified: true` અને `notified_at` આપોઆપ અપડેટ થઈ જશે જેથી કોઈને ફરી ઈમેલ ન જાય.

---

## 🚀 સ્ટેપ-બાય-સ્ટેપ ઉપયોગ કેવી રીતે કરવો (How To Run & Use)

### સ્ટેપ 1: બેકએન્ડ સર્વર શરૂ કરવું (Start Backend)
બેકએન્ડ ફોલ્ડર `C:\Kamal Learning\Deluzex\deluzex-backend` માં:
- **વિકલ્પ A (સૌથી સરળ - એક ક્લિક):** `start_backend.bat` ફાઈલ પર ડબલ ક્લિક કરો.
- **વિકલ્પ B (ટર્મિનલ / Powershell):**
```powershell
& "C:\Kamal Learning\Deluzex\deluzex-backend\venv\Scripts\python.exe" -m uvicorn --app-dir "C:\Kamal Learning\Deluzex\deluzex-backend" main:app --host 0.0.0.0 --port 8000 --reload
```
> બેકએન્ડ હેલ્થ ચેક URL: `http://localhost:8000/`

---

### સ્ટેપ 2: ફ્રન્ટએન્ડ પેજ ઓપન કરવું (Start Frontend)
- **વિકલ્પ A (ડિરેક્ટ બ્રાઉઝર):** `c:\Users\q3tec\Downloads\coming_soon_page\index.html` પર ડબલ-ક્લિક કરીને કોઈપણ બ્રાઉઝરમાં ઓપન કરો.
- **વિકલ્પ B (લોકલ સર્વર - Port 8080):**
```powershell
& "C:\Kamal Learning\Deluzex\deluzex-backend\venv\Scripts\python.exe" -m http.server 8080 --directory "c:\Users\q3tec\Downloads\coming_soon_page"
```
> બ્રાઉઝરમાં ઓપન કરો: `http://localhost:8080`

---

### સ્ટેપ 3: સબસ્ક્રાઇબર્સની સંખ્યા ચેક કરવી (Check Live Stats)
ડેટાબેઝમાં કેટલા લોકોએ સબસ્ક્રાઇબ કર્યું છે અને કેટલાને નોટિફાય કરવાના બાકી છે તે જોવા માટે:
```powershell
& "C:\Kamal Learning\Deluzex\deluzex-backend\venv\Scripts\python.exe" "C:\Kamal Learning\Deluzex\deluzex-backend\send_launch_emails.py" --stats
```

---

### સ્ટેપ 4: બધા સબસ્ક્રાઇબર્સને Excel / CSV માં એક્સપોર્ટ કરવા (Export CSV)
બધા જ ઇમેઇલ્સ અને તારીખો સાથેની CSV ફાઈલ મેળવવા માટે:
```powershell
& "C:\Kamal Learning\Deluzex\deluzex-backend\venv\Scripts\python.exe" "C:\Kamal Learning\Deluzex\deluzex-backend\send_launch_emails.py" --export-csv
```
> ફાઈલ સેવ થશે: `C:\Kamal Learning\Deluzex\deluzex-backend\subscribers.csv`

---

### સ્ટેપ 5: લોન્ચ ઈમેઈલ ટેમ્પલેટ બ્રાઉઝરમાં પ્રિવ્યૂ કરવું (Preview Email)
ગ્રાહકને કેવો સુંદર લક્ઝરી ઈમેલ દેખાશે તે બ્રાઉઝરમાં ચેક કરવા માટે:
```powershell
& "C:\Kamal Learning\Deluzex\deluzex-backend\venv\Scripts\python.exe" "C:\Kamal Learning\Deluzex\deluzex-backend\send_launch_emails.py" --preview
```

---

### સ્ટેપ 6: ફક્ત 1 ટેસ્ટ ઈમેઈલ સેન્ડ કરવો (Send 1 Test Email)
તમારા પોતાના ઈમેઈલ પર ટેસ્ટ ઈમેઈલ મોકલીને ચેક કરવા માટે:
```powershell
& "C:\Kamal Learning\Deluzex\deluzex-backend\venv\Scripts\python.exe" "C:\Kamal Learning\Deluzex\deluzex-backend\send_launch_emails.py" --test your_email@example.com
```

---

### સ્ટેપ 7: વેબસાઇટ લાઈવ થતાં બધાને એક સાથે ઈમેલ મોકલવા (Broadcast Launch Emails)

#### A. સેફ ટેસ્ટ (ડ્રાય રન - કોઈ રિયલ ઈમેલ મોકલ્યા વિના ટેસ્ટ):
```powershell
& "C:\Kamal Learning\Deluzex\deluzex-backend\venv\Scripts\python.exe" "C:\Kamal Learning\Deluzex\deluzex-backend\send_launch_emails.py" --broadcast --dry-run
```

#### B. ફાઇનલ લાઈવ બ્રોડકાસ્ટ (બધા પેન્ડિંગ સબસ્ક્રાઇબર્સને ઈમેલ મોકલશે):
```powershell
& "C:\Kamal Learning\Deluzex\deluzex-backend\venv\Scripts\python.exe" "C:\Kamal Learning\Deluzex\deluzex-backend\send_launch_emails.py" --broadcast
```
> નોંધ: કસ્ટમ વેબસાઇટ લિંક માટે `--url https://deluzex.com` ઉમેરી શકાય છે.

---

## 📧 SMTP / ઈમેઈલ કન્ફિગરેશન (Gmail / Custom Domain)
રિયલ ઈમેઈલ્સ સેન્ડ કરવા માટે `C:\Kamal Learning\Deluzex\deluzex-backend\atlas-credentials.env` અથવા `.env` માં નીચેની વિગતો સેટ કરવી:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_store_email@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx
SMTP_FROM_NAME="de luzex Luxury Lighting"
SMTP_FROM_EMAIL=concierge@deluzex.com
WEBSITE_URL=https://deluzex.com
```

> **Gmail App Password બનાવવાની રીત:**
> 1. તમારા Google Account પર જાઓ -> **Security**
> 2. **2-Step Verification** ઓન કરો
> 3. નીચે **App Passwords** સર્ચ કરો
> 4. 'Deluzex Email' નામ આપી 16 અક્ષરનો App Password મેળવીને `SMTP_PASSWORD` માં મૂકી દો.

---

## 📁 ફાઈલ ડિરેક્ટરી ગાઈડ (Files List)

### 1. `coming_soon_page` ડિરેક્ટરી:
- `index.html` — સિંગલ સ્ટેન્ડઅલોન કમિંગ સૂન પેજ (CSS, JS અને Responsive Layout સાથે)
- `logo.png` — ઓરિજિનલ પારદર્શક હાઈ-રિઝોલ્યુશન લોગો
- `00d77533f67bac5a13fc4b0d78146c44e5ab38f6.png` — લક્ઝરી ઇન્ટિરિયર બેકગ્રાઉન્ડ ઇમેજ
- `README.md` — આ સંપૂર્ણ ગાઈડ ડોક્યુમેન્ટ

### 2. `deluzex-backend` ડિરેક્ટરી:
- `main.py` — FastAPI એપ્લિકેશન
- `start_backend.bat` — બેકએન્ડ શરૂ કરવા માટે ૧-ક્લિક લોન્ચર
- `launch_email_tool.bat` — ઈમેઈલ બ્રોડકાસ્ટ ટૂલ મેનૂ
- `send_launch_emails.py` — લોન્ચ અનાઉન્સમેન્ટ બ્રોડકાસ્ટ સ્ક્રિપ્ટ
- `app/templates/launch_announcement.html` — લક્ઝરી HTML ઈમેઈલ ટેમ્પલેટ
- `app/api/endpoints/newsletter.py` — સબસ્ક્રિપ્શન અને CSV એક્સપોર્ટ API એન્ડપોઇન્ટ્સ
- `app/models/newsletter.py` — ડેટાબેઝ સ્કીમા
