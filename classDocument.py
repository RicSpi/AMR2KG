import penman
import subprocess
from   penman.models.noop import NoOpModel
from amr_coref.amr_coref.coref.inference import Inference

class Document:

    # We would like to store, per article:
    """
    1. Title
    2. Paragraph
    3. Paragraph level AMR ( As discussed, this is less accurate but we can store it anyway since we have it.)
    4. (Sentence, Sentence AMR, Sentence AMR with metadata)
    5. RDF Graphs per sentence. This will be generated with while processing the docs. 
    """
    ## Let us create a Class representing each Document

    def __init__(self, title, paragraph, paragraph_amr, sentences):
        self.title = title
        self.paragraph = paragraph
        self.paragraph_amr = paragraph_amr
        # Sentences will be a list of 3 tuples with first element plain text and second AMR, third AMR with metadata
        self.sentences = sentences
        self.sentences_rdf = []  # Initialize empty list for storing RDF data
        self.coreference_clusters = {}  # Initialize empty dictionary for storing coreference clusters


    def resolve_coreference(self, model_dir='amr_coref/data/model_coref-v0.1.0/', device='cpu'):
        # Load the model and test data
        inference = Inference(model_dir, device=device)

        # Load AMR graphs from the Document object
        ordered_pgraphs = self.load_amr_graphs()

        # Cluster the data
        cluster_dict = inference.coreference(ordered_pgraphs)

        # Store the coreference information in your Document instance
        self.coreference_clusters = cluster_dict
        
        return self.coreference_clusters


    def load_amr_graphs(self):
        """
        Load AMR graphs in penman format from the Document object.
        Needed for the co-reference resolution module.
        Returns:
            list: A list of PENMAN graphs.
        """
        ordered_pgraphs = []

        for _, _, amr_metadata in self.sentences:
            # amr_metadata is the string containing the AMR graph plus ::id and ::snt fields in the document
            graph = penman.decode(amr_metadata, model=NoOpModel())
            ordered_pgraphs.append(graph)

        return ordered_pgraphs
    
    def print_coreference_clusters(self, print_sentence=False):
        for key in self.coreference_clusters.keys():
            print(f"Key: {key}")
            for values in self.coreference_clusters[key]:

                # Unpack the tuple with sentence index and variable name
                sentence_id, var_name = values
                # Lookup the current sentence's AMR from self
                sentence , amr_str, _ = self.sentences[sentence_id]

                # Convert AMR string to a Penman graph
                amr_graph = penman.decode(amr_str)

                # Extract variable labels from instances
                # instance.source (the variable name) and instance.target (the word) 
                # are extracted with a list comprehensions via Graph.instances() method 
                variable_labels = {instance.source: instance.target for instance in amr_graph.instances()}

                # Access the word associated with the variable name
                word = variable_labels.get(var_name)

                if word:
                    print(f"  - Sentence id {sentence_id}: {word} | variable name:{var_name}")
                else:
                    print(f"  - Sentence id {sentence_id}: Word not found for variable {var_name}")
                
                # Print the sentence if needed
                if print_sentence:
                    print(f"    Sentence:{sentence}")


                    
    # Using external script with subprocess.Popen
    def convert_amr_to_rdf(self, sentence_id, format_option='n3'):
        
        # Load the sentence AMR with metadata 
        sentence_content = self.sentences[sentence_id][2] 
        
        # Path to the external script
        script_path = 'amr-ld/my_amr_to_rdf.py'

        # Build the subprocess command
        command = [
            'python', script_path,
            '-f', format_option
        ]

        try:
            # Run the external script, communicating via pipes
            with subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True) as process:
                # Write the sentence content to the script's stdin
                rdf_data, _ = process.communicate(input=sentence_content)

                # Store the RDF data Document class
                self.sentences_rdf.append(rdf_data)
        except subprocess.CalledProcessError as e:
            print(f"Error: {e}")
            return


    def process_amr_to_rdf(self):
        # Process AMR to RDF for sentences
        for _, _, amr_meta in self.sentences:
            rdf_content = self.convert_amr_to_rdf(amr_meta)
            self.sentences_rdf.append(rdf_content)