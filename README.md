# FlexiFit AI — Run the App Locally
> AI-powered health & fitness for PCOS, thyroid, and postpartum journeys.

---

##  Setup Instructions (Run Locally)

### 1️. Clone the Repository
```bash
git clone https://github.com/tumblr-byte/flexifit-ai.git
cd flexifit-ai
```

### 2️. Create Virtual Environment
**Create the virtual environment INSIDE the project folder:**
```bash
python -m venv venv
```

**Activate it:**
```bash
# Linux/Mac
source venv/bin/activate

# Windows
.\venv\Scripts\activate
```

### 3️. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4️. Configure Environment Variables
**Create a `.env` file in the root directory of your project:**
```bash
touch .env  # Linux/Mac
# or just create it manually in Windows
```

**Add your credentials to `.env`:**
```env
# example
DJANGO_SECRET_KEY=your_django_secret_key_here
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

```

### 5️. Set Up the Database
**Make sure your MySQL server is running, then:**
```bash
python manage.py makemigrations
python manage.py migrate
```

### 6️. Run the Development Server
```bash
python manage.py runserver
```

**Visit:** http://127.0.0.1:8000/

---

##  Project Structure
```
flexifit-ai/
├── venv/                  # Virtual environment (DON'T commit this)
├── flexifit/              # Your Django app
│   ├── settings.py
│   ├── urls.py
│   └── ...
├── manage.py
├── requirements.txt
├── .env                   # Environment variables (DON'T commit this)
├── .gitignore
└── README.md
```

---


**Made with ❤️ for women's health empowerment**


---







