class Document:
    def __init__(self, title, paragraph, paragraph_amr, sentences):
        self.title = title
        self.paragraph = paragraph
        self.paragraph_amr = paragraph_amr
        # Sentences will be a list of 3 tuples with first element plain text and second AMR, third AMR with metadata
        self.sentences = sentences
        self.sentences_rdf = [] # Initialize empty list for storing RDF data 
    
    # Using external script with subprocess.Popen
    def convert_amr_to_rdf(self, amr_text, format_option='n3'):
        
        command = ["python","amr-ld","amr_to_rdf.py", "-i", "-", "-o", "-", "-f", format_option]     
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate(input=amr_text)
        if process.returncode != 0:
            print(f"Error in converting AMR to RDF: {stderr}")
            return None
        return stdout

    def process_amr_to_rdf(self):
        # Process AMR to RDF for sentences
        for _, _, amr_meta in self.sentences:
            rdf_content = self.convert_amr_to_rdf(amr_meta)
            self.sentences_rdf.append(rdf_content)