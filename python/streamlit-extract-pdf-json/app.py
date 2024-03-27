import streamlit as st
import requests
import jwt
from datetime import datetime
import json
import time
from graphlit_client import Graphlit

# Initialize session state variables if not already done
if 'client' not in st.session_state:
    st.session_state['client'] = None
if 'token' not in st.session_state:
    st.session_state['token'] = None
if 'specification_id' not in st.session_state:
    st.session_state['specification_id'] = None
if 'content_id' not in st.session_state:
    st.session_state['content_id'] = None
if 'environment_id' not in st.session_state:
    st.session_state['environment_id'] = ""
if 'organization_id' not in st.session_state:
    st.session_state['organization_id'] = ""
if 'secret_key' not in st.session_state:
    st.session_state['secret_key'] = ""
if 'content_done' not in st.session_state:
    st.session_state['content_done'] = None
if 'document_markdown' not in st.session_state:
    st.session_state['document_markdown'] = None
if 'document_metadata' not in st.session_state:
    st.session_state['document_metadata'] = None

def extract_content():
    # Define the GraphQL mutation
    query = """
    query ExtractContents($prompt: String!, $specification: EntityReferenceInput, $filter: ContentFilter) {
        extractContents(prompt: $prompt, specification: $specification, filter: $filter) {
            value
            pageNumber
            error
        }
    }
    """

    # Define the variables for the mutation
    variables = {
        "prompt": "Extract data from text into JSON, using the tool provided. If no appropriate data is found, don't return any response.",
        "specification": {
            "id": st.session_state["specification_id"]
        },
        "filter": {
            "id": st.session_state["content_id"]
        }
    }
    response = st.session_state['client'].request(query=query, variables=variables)

    if 'errors' in response and len(response['errors']) > 0:
        error_message = response['errors'][0]['message']
        return None, error_message

    if 'extractContents' in response['data'] and len(response['data']['extractContents']) > 0:
        return response['data']['extractContents'][0]['value'], response['data']['extractContents'][0]['error']

    return None, None

def get_content():
    # Define the GraphQL mutation
    query = """
    query GetContent($id: ID!) {
        content(id: $id) {
            id
            state
            markdown
            document {
                title
                keywords
                author
            }          
        }
    }
    """

    # Define the variables for the mutation
    variables = {
        "id": st.session_state['content_id']
    }

    response = st.session_state['client'].request(query=query, variables=variables)

    if 'content' in response['data']:
        return response['data']['content']['document'], response['data']['content']['markdown']
    
    return None

def is_content_done():
    # Define the GraphQL mutation
    query = """
    query IsContentDone($id: ID!) {
        isContentDone(id: $id) {
            result
        }
    }
    """

    # Define the variables for the mutation
    variables = {
        "id": st.session_state["content_id"]
    }
    response = st.session_state['client'].request(query=query, variables=variables)

    if 'errors' in response and len(response['errors']) > 0:
        error_message = response['errors'][0]['message']
        return None, error_message

    return response['data']['isContentDone']['result'], None

def delete_specification():
    # Define the GraphQL mutation
    query = """
    mutation DeleteSpecification($id: ID!) {
        deleteSpecification(id: $id) {
            id
            state
        }
        }
    """

    # Define the variables for the mutation
    variables = {
        "id": st.session_state['specification_id']
    }
    response = st.session_state['client'].request(query=query, variables=variables)

def create_specification(schema):
    # Define the GraphQL mutation
    mutation = """
    mutation CreateSpecification($specification: SpecificationInput!) {
        createSpecification(specification: $specification) {
            id
            name
            state
            type
            serviceType
        }
    }
    """

    # Define the variables for the mutation
    variables = {
        "specification": {
            "type": "EXTRACTION",
            "serviceType": "OPENAI",
            "openAI": {
                "model": "GPT4_TURBO_128K",
                "temperature": 0.1,
                "probability": 0.2,
                "completionTokenLimit": 2048
            },
            "tools": [
                {
                    "name": "extractJSON",
                    "schema": schema
                }
            ],
            "name": "Extraction"
        }
    }

    # Convert the request to JSON format
    response = st.session_state['client'].request(query=mutation, variables=variables)

    if 'errors' in response and len(response['errors']) > 0:
        error_message = response['errors'][0]['message']
        return error_message

    st.session_state['specification_id'] = response['data']['createSpecification']['id']

    return None

def delete_content():
    # Define the GraphQL mutation
    query = """
    mutation DeleteContent($id: ID!) {
        deleteContent(id: $id) {
            id
        }
        }
    """

    # Define the variables for the mutation
    variables = {
        "id": st.session_state['content_id']
    }

    response = st.session_state['client'].request(query=query, variables=variables)

def ingest_file(uri):
    # Define the GraphQL mutation
    mutation = """
    mutation IngestFile($uri: URL!) {
        ingestFile(uri: $uri) {
            id
        }
    }
    """

    # Define the variables for the mutation
    variables = {
        "uri": uri
    }

    # Convert the request to JSON format
    response = st.session_state['client'].request(query=mutation, variables=variables)

    if 'errors' in response and len(response['errors']) > 0:
        error_message = response['errors'][0]['message']
        return error_message

    st.session_state['content_id'] = response['data']['ingestFile']['id']

    return None

st.image("https://graphlitplatform.blob.core.windows.net/samples/graphlit-logo.svg", width=128)
st.title("Graphlit Platform")
st.markdown("Extract JSON from any PDF, DOCX, or PPTX file.")

if st.session_state['token'] is None:
    st.info("To get started, generate a token to connect to your Graphlit project.")

# A dictionary mapping PDF names to their PDF URIs
pdfs = {
    "Uber Prepared Remarks (Q4 2023)": "https://graphlitplatform.blob.core.windows.net/samples/Uber-Q4-23-Prepared-Remarks.pdf",
    "Microsoft 10Q (March 2024)": "https://graphlitplatform.blob.core.windows.net/samples/MSFT_FY24Q1_10Q.docx",
    "Uber 10Q (March 2022)": "https://graphlitplatform.blob.core.windows.net/samples/uber_10q_march_2022.pdf",
    "Attention is all you need": "https://graphlitplatform.blob.core.windows.net/samples/Attention%20Is%20All%20You%20Need.1706.03762.pdf",
    "Unifying Large Language Models and Knowledge Graphs: A Roadmap": "https://graphlitplatform.blob.core.windows.net/samples/Unifying%20Large%20Language%20Models%20and%20Knowledge%20Graphs%20A%20Roadmap-2306.08302.pdf",
}

document_metadata = None
document_markdown = None

with st.form("data_content_form"):
    selected_pdf = st.selectbox("Select a PDF:", options=list(pdfs.keys()))
    
    document_uri = st.text_input("Or enter your own URL to a file (i.e. PDF, DOCX, PPTX):", key='pdf_uri')

    uri = document_uri if document_uri else pdfs[selected_pdf]

    submit_content = st.form_submit_button("Submit")

    # Now, handle actions based on submit_data outside the form's scope
    if submit_content and uri:
        st.session_state.messages = []
        st.session_state['content_done'] = False

        if st.session_state['token']:
            st.session_state['uri'] = uri
            
            # Clean up previous session state
            if st.session_state['content_id'] is not None:
                with st.spinner('Deleting existing content... Please wait.'):
                    delete_content()
                st.session_state["content_id"] = None

            else:
                error_message = ingest_file(uri)

                if error_message is not None:
                    st.error(f"Failed to ingest file [{uri}]. {error_message}")
                else:
                    start_time = time.time()

                # Display spinner while processing
                with st.spinner('Ingesting document... Please wait.'):
                    done = False
                    time.sleep(2)
                    while not done:
                        done, error_message = is_content_done()

                        if error_message is not None:
                            st.error(f"Failed to wait for content to be done. {error_message}")
                            done = True                                

                        # Wait a bit before checking again
                        if not done:
                            time.sleep(2)
                # Once done, notify the user
                st.session_state["content_done"] = True

                duration = time.time() - start_time

                current_time = datetime.now()
                formatted_time = current_time.strftime("%H:%M:%S")

                st.success(f"Document ingestion took {duration:.2f} seconds. Finished at {formatted_time} UTC.")

                document_metadata, document_markdown = get_content()

                st.session_state['document_metadata'] = document_metadata
                st.session_state['document_markdown'] = document_markdown

                placeholder = st.empty()
        else:
            st.error("Please fill in all the connection information.")

if st.session_state['content_done'] == True:
    if st.session_state['token']:
        st.markdown(f"**Document URI:** {uri}")

        document_metadata = st.session_state['document_metadata']
        document_markdown = st.session_state['document_markdown']

        if document_metadata is not None:
            document_title = document_metadata["title"]
            document_author = document_metadata["author"]

            if document_title is not None:
                st.markdown(f"**Title:** {document_title}")

            if document_author is not None:
                st.markdown(f"**Author:** {document_author}")

        if document_markdown is not None:
            with st.expander("See document text:", expanded=False):
                st.markdown(document_markdown)

        placeholder = st.empty()

        default_schema = """
        {
            "type": "object",
            "properties": {
                "term": {
                "type": "string",
                "description": "A term or key phrase, which can be searched on the web"
                }
            },
            "required": [
                "term"
            ]
        }
        """

        if 'schema' not in st.session_state:
            st.session_state['schema'] = default_schema.strip()

        # Create two columns
        col1, col2 = st.columns(2)

        # Input JSON in the first column
        with col1:
            schema = st.text_area("Enter JSON schema to be extracted:", value=st.session_state["schema"], height=300)

            st.session_state["schema"] = schema

            submit_extract = st.button("Extract JSON")

            if submit_extract:
                if st.session_state['specification_id'] is not None:
                    with st.spinner('Deleting existing specification... Please wait.'):
                        delete_content()
                    st.session_state["specification_id"] = None

                if st.session_state['specification_id'] is None:
                    error_message = create_specification(schema)

                    if error_message is not None:
                        st.error(f"Failed to create specification. {error_message}")

                response, error_message = extract_content()
                
                if error_message is not None:
                    st.error(f"Failed to extract JSON. {error_message}")

                placeholder.json(response)

        # Attempt to format and display the JSON in the second column as it's being edited
        with col2:
            if schema:
                try:
                    # Format the JSON input
                    formatted_json = json.dumps(json.loads(schema), indent=2)

                    st.code(formatted_json, language='json')
                except json.JSONDecodeError:
                    st.error("Invalid JSON schema.")

with st.sidebar:
    st.info("""
        ### Demo Instructions
        - [Sign up for Graphlit](https://docs.graphlit.dev/getting-started/signup) 🆓  
        - **Step 1:** Generate Graphlit project token.
        - **Step 2:** Select a PDF, or fill in your own document URL.
        - **Step 3:** Enter JSON schema for data to be extracted.
        - **Step 4:** View JSON extracted from document text.
        """)

    with st.form("credentials_form"):
        st.info("Locate connection information for your project in the [Graphlit Developer Portal](https://portal.graphlit.dev/)")

        st.text_input("Organization ID", value=st.session_state['organization_id'], key="organization_id")
        st.text_input("Preview Environment ID", value=st.session_state['environment_id'], key="environment_id")
        st.text_input("Secret", value=st.session_state['secret_key'], key="secret_key")

        submit_credentials = st.form_submit_button("Generate Token")
        
        if submit_credentials:
            if st.session_state['secret_key'] and st.session_state['environment_id'] and st.session_state['organization_id']:
                st.session_state['client'] = Graphlit(environment_id=st.session_state['environment_id'], organization_id=st.session_state['organization_id'], secret_key=st.session_state['secret_key'])
                st.session_state['token'] = st.session_state['client'].token

                st.success("Token generated successfully.")
            else:
                st.error("Please fill in all the connection information.")

    st.markdown("""
        [Support on Discord](https://discord.gg/ygFmfjy3Qx)            
        [API Reference](https://docs.graphlit.dev/graphlit-data-api/api-reference)     
        [More information](https://www.graphlit.com)      
        """)