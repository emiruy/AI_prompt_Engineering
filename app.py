    
from langchain_tavily import TavilySearch
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
import streamlit as st
from dotenv import load_dotenv
from fpdf import FPDF
import io, os

# 🔑 API KEYS
os.environ["TAVILY_API_KEY"] = "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"
api_key = st.secrets["GROQ_API_KEY"]

# Initialize LLM
llm = ChatGroq(model="openai/gpt-oss-20b", api_key=api_key)

# Tool
search_tool = TavilySearch(topic="general", max_results=2)

# ================= FUNCTIONS =================
def extract_file_content(uploaded_file):
    """Optional: extract text if user uploads a deck/overview"""
    if uploaded_file is None:
        return ""
    try:
        if uploaded_file.name.endswith(".pdf"):
            from PyPDF2 import PdfReader
            reader = PdfReader(uploaded_file)
            return "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
        elif uploaded_file.name.endswith(".docx"):
            import docx
            doc = docx.Document(uploaded_file)
            return "\n".join([p.text for p in doc.paragraphs])
        else:
            return uploaded_file.read().decode("utf-8", errors="ignore")
    except Exception as e:
        return f"[Error parsing file: {e}]"

def generate_insights(company_name, product_name, company_url, company_competitors,
                      product_category, value_proposition, target_customer, file_content=""):
    # Perform Tavily search
    search_query = f"site:{company_url} company strategy leadership competitors business model"
    search_results = search_tool.invoke(search_query)

    # Prompt engineering
    messages = [
        SystemMessage("You are a sales assistant. Provide a concise, structured, one-page account insight."),
        HumanMessage(content=f"""
        Inputs:
        - Company: {company_name}
        - Product: {product_name}
        - Category: {product_category}
        - Value Proposition: {value_proposition}
        - Target Customer: {target_customer}
        - Competitors: {company_competitors}
        - Uploaded Product Info: {file_content[:1500]}  # truncated if long
        - Tavily Search Results: {search_results}

        Task:
        Generate a professional one-pager with the following sections:
        1. Company Strategy
        2. Competitor Mentions
        3. Leadership & Decision Makers
        4. Product/Strategy Summary (link to industry trends, 10-Ks if public)
        5. Sources / Article Links

        Make it clear, bullet-pointed, and concise. 
        """)
    ]

    model_response = llm.invoke(messages)
    return model_response.content

def create_pdf(report_text, company_name):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    safe_text = report_text.encode("latin-1", "replace").decode("latin-1")
    pdf.multi_cell(0, 10, safe_text)

    pdf_buffer = io.BytesIO()
    pdf.output(pdf_buffer, 'S')
    return pdf_buffer.getvalue()

# ================= UI =================
st.title("Sales Assistant Agent")
st.subheader("Generate Account Insights")
st.divider()

company_name = st.text_input("Company Name")
company_url = st.text_input("Company URL")
product_name = st.text_input("Product Name")
product_category = st.text_input("Product Category")
company_competitors = st.text_input("Company Competitors")
value_proposition = st.text_area("Value Proposition")
target_customer = st.text_input("Target Customer")
uploaded_file = st.file_uploader("Optional: Upload Product Overview (PDF/DOCX/TXT)", type=["pdf","docx","txt"])

if st.button("Generate Report"):
    if company_name and company_url:
        with st.spinner("Generating Report..."):
            file_content = extract_file_content(uploaded_file)
            result = generate_insights(company_name, product_name, company_url, company_competitors,
                                       product_category, value_proposition, target_customer, file_content)

            st.divider()
            st.write(result)

            if result:
                st.download_button("Download Report (TXT)", result, file_name="sales_report.txt", mime="text/plain")

                pdf_data = create_pdf(result, company_name)
                st.download_button("Download Report (PDF)", pdf_data,
                                   file_name=f"sales_report_{company_name}.pdf",
                                   mime="application/pdf")
    else:
        st.warning("Please enter at least a company name and URL")
