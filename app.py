import streamlit as st
st.set_page_config(
    page_title="Enterprise RAG Assistant",
    page_icon="Test Icon",
    layout= "wide"
)

st.title("Enterprise Document Intelligence")
st.write("An AI-powered document question-answering system "
    "using Retrieval-Augmented Generation (RAG).")

st.sidebar.title("Project Information")
st.sidebar.write("Enterprise RAG Assistant")

st.sidebar.subheader("System Status")
st.sidebar.success("Application running")

st.header("Welcome")

st.write(
    "Upload your documents and ask questions "
    "to retrieve relevant information."
)

#Document Uploader
uploaded_files = st.file_uploader(
    "Please upload your documents", type=["pdf", "docx", "txt"],
    accept_multiple_files=True,
    help="Upload one or more documents to analyze"    
)

if uploaded_files:
    st.success(f"{len(uploaded_files)} documents uploaded successfully.")


#Display uploaded documents
for file in uploaded_files:
        file_details = {
            "filename": file.name,
            "filetype": file.type,
            "filesize": file.size
        }
        st.write("**File Details:**", file_details)
        
        