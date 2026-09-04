# EventOS – Event Management System

## 📌 About the Project

**EventOS** is a web-based event management system developed using Django. The main purpose of this project is to make event management easier and more organized.

The system provides a single platform where administrators can manage events, categories, members, contacts, and reports. Instead of managing event information manually, everything can be handled through the web application.

We are also adding an **AI Assistant** to EventOS. The AI assistant allows users to ask questions about events and the system in normal language, making the application easier and more interactive to use.

---

## 🎯 Objectives

The main objectives of EventOS are:

* To provide a simple platform for managing events.
* To organize events using categories.
* To manage members and event-related information.
* To provide a dashboard for easier management.
* To generate useful reports.
* To reduce manual work.
* To improve the user experience using an AI assistant.

---

## ✨ Main Features

### 🔐 Authentication

Users can securely log in and access the features available to them.

### 📅 Event Management

Administrators can create, view, update, and delete events. Event information can be managed from one place.

### 🗂️ Category Management

Events can be organized into different categories, making them easier to manage and find.

### 👥 Member Management

The system provides functionality for managing member or participant information.

### 📊 Dashboard & Reports

The dashboard gives a quick overview of the system, while reports help administrators understand event-related information.

### 📩 Contact

Users can use the contact section to send queries, feedback, or other messages.

---

## 🤖 AI Event Assistant

The AI Assistant is one of the main new features being added to EventOS.

Instead of searching through different pages, users can simply ask questions such as:

```text
What events are available?

Show me upcoming events.

Which technology events are available?

How do I create an event?

What is EventOS?
```

The assistant processes the user's question and provides a relevant response.

### How it works

```text
User
  ↓
Chatbot Interface
  ↓
Django Backend
  ↓
Event Data / AI Service
  ↓
AI Response
  ↓
User
```

The AI API will be connected through the Django backend so that the API key is not exposed in the frontend.

---

## 🛠️ Technologies Used

* **Python** – Backend programming
* **Django** – Web framework
* **HTML, CSS & JavaScript** – Frontend
* **Database** – Stores application data
* **AI API** – AI Assistant
* **Docker** – Application containerization
* **Git & GitHub** – Version control

---

## 📂 Project Structure

```text
EventOS/
│
├── EventManagement/
├── event/
├── templates/
├── static/
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

The Django project contains the main configuration, while the application files handle event-related functionality. Templates and static files are used for the user interface.

---

## ⚙️ Installation

### 1. Clone the repository

```bash
git clone https://github.com/akshay25ds153/EventOS.git
cd EventOS
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

Activate it on Windows:

```bash
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run migrations

```bash
python manage.py migrate
```

### 5. Start the server

```bash
python manage.py runserver
```

The application can then be opened in the browser using the local Django server address.

---

## 🔑 AI Configuration

The AI API key should be stored in an environment variable instead of being written directly into the source code.

Example:

```env
AI_API_KEY=your_api_key_here
```

The actual API key should **never be uploaded to GitHub**.

---

## 🔮 Future Improvements

Some features that can be added in the future include:

* AI-based event recommendations
* Voice-based AI assistant
* Multilingual chatbot
* Email/event notifications
* Calendar integration
* Attendance tracking
* Advanced analytics
* Mobile application

---

## 📌 Conclusion

EventOS is designed to make event management simpler and more organized. It brings different event-management activities into one platform and reduces the need for manual work.

With the addition of the AI Assistant, users can interact with the system more naturally and quickly find the information they need.

The project also provides practical experience with **Django, databases, frontend development, APIs, AI integration, Docker, and GitHub**.

---

## 🔗 Project Repository

**GitHub:**
https://github.com/akshay25ds153/EventOS

## 👨‍💻 Project

**Project Name:** EventOS
**Type:** Event Management System
**Backend:** Django / Python
**Frontend:** HTML / CSS / JavaScript
**AI:** AI-powered Event Assistant
