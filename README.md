# 🛒 Bakery Course Booking System using Semantic Web


## 🙏🏻 Acknowledgment

We gratefully acknowledge that this project is based on the original implementation by **[Yeo Quan Xiang](https://github.com/8Lank1412)**. His system served as the foundation, and we have built upon it by adding new features and enhancements.


## 📌 Introduction  

The **Bakery Course Booking System** is a web-based application designed to streamline the registration and payment process for baking courses. Leveraging Semantic Web technologies—such as XML for calendar exports, RDF/RDFS for structured receipt data, and SPARQL for receipt validation—the system offers a robust, user-friendly platform for both customers and administrators.


## ❗ Problem Statements

🔸 **Insufficient Booking Validation** - Without rigorous input checks, users can overbook classes, create duplicate registrations, or submit incomplete information, leading to manual conflict resolution and errors. <br>
🔸 **Lack of Structured Course Calendar** - After enrollment, customers lack an exportable, machine-readable schedule, causing confusion over class dates and times—especially when booking multiple courses. <br>
🔸 **Inadequate Receipt Verification** - Plain-text receipts are prone to errors and fraud. Mismatched dates, amounts, or course details can delay enrollment and diminish user trust.


## 🎯 Objectives  

✅ **Implement Robust Validation**: Use **RDF/RDFS and SPARQL** to enforce business rules—such as capacity limits and single-registration constraints—and ensure data integrity. <br>
✅ **Provide Exportable Course Calendars**: Generate **XML-based schedules** that customers can download and reference offline, improving their planning and attendance. <br>
✅ **Establish Secure Receipt Validation**: Validate digital receipts in **Turtle format** against server data using **SPARQL queries** to prevent manipulation or fraud.


## 🔥 System Features  

🚀 **Flask & Python Backend** - Built on Flask with SQLAlchemy for ORM, Flask-Login for authentication, and Bcrypt for password hashing. <br>
🖥️ **Responsive Frontend** - HTML templates with Jinja2, Bootstrap for styling, and Flask-WTF for form handling. <br>
📅 **XML Calendar Export** - Users can download their course schedules in a structured, **human-readable XML format**. <br>
📜 **RDF/RDFS Modeling** - Digital receipts are represented as **RDF graphs (Turtle)**, defining `Receipt`, `User`, and `Course` classes with semantic properties. <br>
🔍 **SPARQL Validation** - Automated **SPARQL queries** check receipt authenticity, user identity, course details, and financial accuracy. <br>
👤 **Admin Interface** - Separate login for administrators to manage student data and export student lists per course as XML.


## 🛠️ Installation Guide  

1️⃣ **Clone the repository**

```bash
git clone https://github.com/rydzze/Bakery-Course-Booking-System.git
cd Bakery-Course-Booking-System
```

2️⃣ **Create a virtual environment**

```bash
python -m venv venv
```

3️⃣ **Install dependencies (activate venv first)**

```bash
pip install -r requirements.txt
```

4️⃣ **Run the application**

```bash
python run.py
```

5️⃣ **Access the system via:** 🌍

```
http://localhost:5000
```


## 🏆 Contribution

We would like to thank the following team members for their contributions:

- [Muhammad Ariff Ridzlan](https://github.com/rydzze)
- [Noor Alia Alisa](https://github.com/alia4lisa)
- [Jason Tan Khim Chen](https://github.com/Xiaocu20)
- [Yeo Quan Xiang](https://github.com/8Lank1412)
