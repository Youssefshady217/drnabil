import streamlit as st
import pdfplumber
import pandas as pd
from io import BytesIO
from fpdf import FPDF
import arabic_reshaper
from bidi.algorithm import get_display
import os

# إعدادات الصفحة
st.set_page_config(page_title="صيدلية د/ نادر", layout="centered")

def reshape_arabic(text):
    return get_display(arabic_reshaper.reshape(str(text)))

# تسجيل الدخول
VALID_USERNAME = "romany"
VALID_PASSWORD = "4321"

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 تسجيل الدخول")

    with st.form("login_form"):
        username = st.text_input("اسم المستخدم")
        password = st.text_input("كلمة المرور", type="password")
        login = st.form_submit_button("دخول")

        if login:
            if username == VALID_USERNAME and password == VALID_PASSWORD:
                st.session_state.logged_in = True
                st.success("✅ تم تسجيل الدخول بنجاح")
                st.rerun()
            else:
                st.error("❌ اسم المستخدم أو كلمة المرور غير صحيحة")
    st.stop()

# عنوان التطبيق
st.title("د/نادر نبيل فهمى")

# رفع ملف PDF
uploaded_file = st.file_uploader("📤 ارفع ملف PDF يحتوي على جدول", type=["pdf"])

if uploaded_file:
    with pdfplumber.open(uploaded_file) as pdf:
        full_text = ""
        table_data = []
        for page in pdf.pages:
            full_text += page.extract_text() + "\n"
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    table_data.append(row)

    # استخراج بيانات العميل
    first_name = ""
    last_name = ""
    client1_name = ""
    insurance_company = ""
    dispensed_date = ""
    import re

    lines = full_text.split("\n")
    for i, line in enumerate(lines):
    # مطابقة First Name
        if "First Name" in line:
            match = re.search(r"First Name\s*:\s*(\S+)", line)
            if match:
                first_name = match.group(1).strip()

    # مطابقة Last Name
        if "Last Name" in line:
            match = re.search(r"Last Name\s*:\s*(\S+)", line)
            if match:
               last_name = match.group(1).strip()

        if "Insurance Company" in line:
            parts = line.split(":")
            if len(parts) > 1:
                insurance_company = parts[1].strip()
        if "Service Date" in line:
            match = re.search(r"Service Date\s*:\s*(\d{2}/\d{2}/\d{4})", line)
            if match:
                dispensed_date = match.group(1)
    client1_name = f"{last_name} {first_name}".strip()

    df = pd.DataFrame(table_data)

    # تحديد رأس الجدول
    header_row_index = None
    for i, row in df.iterrows():
        if any("Quantity" in str(cell) for cell in row):
            header_row_index = i
            break

    if header_row_index is not None:
        df.columns = df.iloc[header_row_index]
        df = df.drop(index=range(0, header_row_index + 1)).reset_index(drop=True)
        df.columns = df.columns.str.strip()

        required_cols = ["Status", "Quantity", "Price (per\npackage)", "Total\nPrice", "Name"]
        if all(col in df.columns for col in required_cols):
            df = df[df["Status"].str.contains("Approved", na=False)]

            df["Price (per\npackage)"] = df["Price (per\npackage)"].str.extract(r"(\d+\.?\d*)").astype(float)
            df["Total\nPrice"] = df["Total\nPrice"].str.extract(r"(\d+\.?\d*)").astype(float)

            df["اسم الصنف"] = df["Name"]
            df["الكمية"] = df["Quantity"]
            df["سعر الوحدة"] = df["Price (per\npackage)"]
            df["سعر الكمية"] = df["Total\nPrice"].round(2)

            final_df = df[["اسم الصنف", "الكمية", "سعر الوحدة", "سعر الكمية"]]

            st.success(f"✅ تم استخراج {len(final_df)} صنف معتمد")
            edited_df = st.data_editor(final_df, num_rows="dynamic", use_container_width=True)

            # تحميل Excel
            output = BytesIO()
            edited_df.to_excel(output, index=False)
            output.seek(0)

            st.download_button(
                label="⬇️ تحميل Excel",
                data=output,
                file_name="approved_meds.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            # توليد PDF
            if st.button("📄 توليد إيصال PDF"):
                class PDF(FPDF):
                    def header(self):
                        pdf.add_font("Amiri", "", "Amiri-Regular.ttf", uni=True)
                        self.add_font("Amiri", "B", "Amiri-Bold.ttf", uni=True)
                        self.set_fill_color(230, 230, 230)
                        self.image("logo.png", x=10, y=8, w=20)
                        self.set_font("Amiri", "B", 14)
                        self.cell(0, 10, reshape_arabic("صيدلية د/ نادر نبيل فهمى"), ln=1, align="C")
                        self.set_font("Amiri", "", 11)
                        self.cell(0, 10, reshape_arabic("م.ض: 01-40-181-00591-5"), ln=1, align="C")
                        self.cell(0, 10, reshape_arabic("س.ت: 94294"), ln=1, align="C")
                        self.set_font("Amiri", "", 10)
                        self.cell(0, 10, reshape_arabic("العنوان: اسيوط - شركه فريال - شارع الامام علي"), ln=1, align="C")
                        self.cell(0, 10, reshape_arabic("تليفون: 01211136366"), ln=1, align="C")
                        self.ln(5)

                    def footer(self):
                        self.set_y(-20)
                        self.set_font("Amiri", "", 10)
                        self.set_text_color(100)
                        self.cell(0, 10, reshape_arabic("شكراً لتعاملكم معنا ❤"), ln=1, align="C")
                        self.cell(0, 10, reshape_arabic(f"صفحة رقم {self.page_no()}"), align="C")

                pdf = PDF()
                pdf.add_page()
                pdf.set_font("Amiri", "", 11)

                # بيانات العميل
                reshaped1_name = reshape_arabic(client1_name)
                reshaped_label = reshape_arabic("اسم العميل: ")
                pdf.cell(0, 10, client1_name + reshaped_label , ln=1, align="R")
                pdf.cell(0, 10, reshape_arabic("شركة التأمين: شركة مصر للتامين " ), ln=1, align="R")
                pdf.cell(0, 10, reshape_arabic("التاريخ: " + dispensed_date), ln=1, align="R")
                pdf.ln(5)

                # رأس الجدول
                headers = ["اسم الصنف", "الكمية", "سعر الوحدة", "سعر الكمية"]
                col_widths = [80, 25, 30, 35]
                row_height = 10
                rows_per_page = 25
                row_count = 0

                def draw_table_header():
                    pdf.set_fill_color(230, 230, 230)
                    pdf.set_font("Amiri", "B", 12)
                    for i, h in enumerate(headers):
                        pdf.cell(col_widths[i], row_height, reshape_arabic(h), border=1, align="C", fill=True)
                    pdf.ln()

                draw_table_header()

                for index, row in edited_df.iterrows():
                    if row_count >= rows_per_page:
                        pdf.add_page()
                        draw_table_header()
                        row_count = 0

                    pdf.cell(col_widths[0], row_height, reshape_arabic(row["اسم الصنف"]), border=1, align="C")
                    pdf.cell(col_widths[1], row_height, reshape_arabic(str(row["الكمية"])), border=1, align="C")
                    pdf.cell(col_widths[2], row_height, reshape_arabic(str(row["سعر الوحدة"])), border=1, align="C")
                    pdf.cell(col_widths[3], row_height, reshape_arabic(str(row["سعر الكمية"])), border=1, align="C")
                    pdf.ln()
                    row_count += 1

                pdf.ln(5)
                pdf.cell(0, 10, reshape_arabic(f"عدد الأصناف: {len(edited_df)}"), ln=1, align="R")
                pdf.cell(0, 10, reshape_arabic(f"الإجمالي: {edited_df['سعر الكمية'].sum():.2f} EGP"), ln=1, align="R")

                # حفظ PDF في ذاكرة مؤقتة
                pdf_output = pdf.output(dest='S')
                if isinstance(pdf_output, str):
                    pdf_output = pdf_output.encode('latin-1')

                pdf_buffer = BytesIO(pdf_output)

                base_name = os.path.splitext(uploaded_file.name)[0]
                output_name = f"{base_name}_receipt.pdf"

                st.download_button(label="⬇️ تحميل إيصال PDF", data=pdf_buffer, file_name=output_name, mime="application/pdf")

        else:
            st.error("❌ بعض الأعمدة المطلوبة غير موجودة في الجدول.")
    else:
        st.error("❌ لم يتم العثور على صف يحتوي على كلمة 'Quantity' لتحديد رأس الجدول.")
