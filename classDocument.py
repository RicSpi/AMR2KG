import penman
import subprocess
import re
import rdflib
from rdflib.namespace import RDF, RDFS
from pyvis.network import Network
import networkx as nx
from penman.models.noop import NoOpModel
from amr_coref.amr_coref.coref.inference import Inference

class Document:
    """
    Represents a document with the following attributes:

    Attributes:
        title (str): The title of the document.
        paragraph (str): The content of the document's paragraph.
        paragraph_amr (str): The AMR of the document's paragraph.
        sentences (list): A list of 3-tuples representing sentences in the document.
                          Each tuple contains plain text, AMR, and AMR with metadata.
        sentences_rdf (list): A list for storing RDF graphs generated while processing the document.
        coreference_clusters (dict): A dictionary for storing coreference clusters in the document.

    Example:
        doc = Document('Sample Document', 'This is a sample paragraph.', 'AMR of the paragraph', 
                       [('Sentence 1', 'AMR 1', 'AMR 1 with metadata'), ('Sentence 2', 'AMR 2', 'AMR 2 with metadata')])
    """

    def __init__(self, title, paragraph, paragraph_amr, sentences):
        self.title = title
        self.paragraph = paragraph
        self.paragraph_amr = paragraph_amr
        # Sentences will be a list of 3 tuples with first element plain text and second AMR, third AMR with metadata
        self.sentences = sentences
        self.sentences_rdf = []  # Initialize empty list for storing RDF data
        self.coreference_clusters = {}  # Initialize empty dictionary for storing coreference clusters

    ## COREFERENCE METHODS ##
        
    def resolve_coreference(self, model_dir='amr_coref/data/model_coref-v0.1.0/', device='cpu'):
        """
        Resolve coreference in AMR graphs using a pre-trained model.

        Args:
        model_dir (str, optional): Directory containing the coreference resolution model (default is 'amr_coref/data/model_coref-v0.1.0/').
        device (str, optional): Device for model inference (default is 'cpu', cuda:0 for GPU).

        Returns:
        dict: A dictionary containing coreference clusters.
        """
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
        """
        Print coreference clusters and associated information. 
        Useful for evaluation and debugging.

        Args:
        print_sentence (bool, optional): Whether to print the sentence associated with each cluster (default is False).

        Returns:
        None.

        Example:
        document.print_coreference_clusters() prints coreference clusters, variable names, and associated words.
        """

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

    ## AMR2RDF METHODS ##

    def convert_amr_to_rdf(self, sentence_id, format_option='n3'):
        """
        Converts an Abstract Meaning Representation (AMR) to Resource Description Framework (RDF) format
        using an external script through subprocess.Popen.

        Args:
        sentence_id (int): The index of the sentence in 'sentences' to convert.
        format_option (str, optional): The RDF serialization format option (default is 'n3', Turtle format).

        Raises:
        subprocess.CalledProcessError: If the external script execution encounters an error.

        Returns:
        None: The RDF data is stored in 'sentences_rdf' attribute.

        Example:
        Consider 'sentences' with AMR  and calling convert_amr_to_rdf(0) would convert
        the first sentence's AMR to RDF using the 'n3' format and store the result in 'sentences_rdf'.

        TO_DO: Decouple this from the sentence id, so that it can be used in more scenarios.
        """
        
        # Load the sentence AMR with metadata 
        sentence_content = self.sentences[sentence_id][2] 
        # Path to the external script (this file is the butchered version of the OG)
        script_path = 'amr-ld/my_amr_to_rdf.py'
        # Build the subprocess command
        command = [
            'python', script_path,
            '-f', format_option
        ]

        try:
            # Run the external script, communicating via pipes (How this is working is kinda obscure to me)
            with subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True) as process:
                # Write the sentence content to the script's stdin
                rdf_data, _ = process.communicate(input=sentence_content)
                # Store the RDF data Document class
                self.sentences_rdf.append(rdf_data)
        except subprocess.CalledProcessError as e:
            print(f"Error: {e}")
            return

    def all_sentences_to_rdf(self):
        """
        Converts all sentences in the instance to RDF format.

        This function iterates through the list of sentences stored in the instance
        and calls the 'convert_amr_to_rdf' method for each sentence.

        Parameters:
        - self: The instance of the class containing the 'sentences' attribute.
        Returns:
        None
        """

        for index, sentence_tuple in enumerate(self.sentences):
            self.convert_amr_to_rdf(index)

    ## GRAPHS
            
    def generate_document_rdf(self):
        """
        Generates RDF Graph for the entire document based on individual sentence RDF graphs.

        This method combines RDF graphs generated for individual sentences. 
        Iterates through the 'sentences_rdf' attribute, parses each sentence's RDF data
        and adds it to the 'document_rdf_graph'. The resulting RDF graph for the entire document is then returned.

        It handles errors for non-initialized sentence_rdf attribute (<2) and parsing errors.

        Parameters:
        - self: The instance of the class containing the 'sentences_rdf' attribute.

        Returns:
        A combined RDF graph representing the entire document.
        """

        document_rdf_graph = rdflib.Graph()
        try:
            # Check if there are less than two sentences
            if len(self.sentences_rdf) < 2:
                raise ValueError("Insufficient sentences to generate document RDF. Process all sentences first.")

            for graph in self.sentences_rdf:
                temp_graph = rdflib.Graph()
                document_rdf_graph += temp_graph.parse(data=graph, format="n3")

        except Exception as e:
            print(f"Error generating document RDF: {e}")
            # Handle the error as needed; the returned RDF graph may be incomplete.
        return document_rdf_graph
    

    def link_coreference_in_rdf(self):
        """
        Links coreferencing variables in the document-level RDF graph.

        Converts all sentences to RDF, generates a document-level RDF graph,
        defines the coreference namespace, generates cluster URIs, and iterates
        over coreference clusters to add nodes representing the clusters and links
        variables to the coreference cluster nodes using 'sameAs' edge.

        Returns:
        rdflib.Graph: The document-level RDF graph with coreference links.
        """
        # Convert all sentences to RDF
        self.all_sentences_to_rdf()

        # Generate document-level RDF graph
        g = self.generate_document_rdf()

        # Define the coreference namespace
        coreference = rdflib.Namespace("http://example.org/cluster/")
        # Extract the article namespace dynamically from the first sentence's AMR representation
        article_namespace = self.extract_article_namespace()

        # Generate relations clusters URIs
        relations_uris = self.generate_clusters_uris()

        # Iterate over coreference clusters
        for relation, cluster in self.coreference_clusters.items():
            # if coref clusters are initialized
            if len(cluster) > 1:
                # Access cluster URI 
                relation_node_uri = relations_uris[relation]

                # Add a new node representing the coreference cluster
                g.add((rdflib.URIRef(relation_node_uri), RDF.type, coreference.Cluster))
                g.add((rdflib.URIRef(relation_node_uri), RDFS.label, rdflib.Literal(f"Cluster {relation}")))

                # Link variables to the coreference cluster node using 'sameAs' edge
                for sentence_index, variable_name in cluster:

                    # Construct the URI for the variable node
                    variable_node_uri = f"http://amr.isi.edu/amr_data/{article_namespace}.sent{sentence_index + 1}#{variable_name}"

                    # Link the variable node to the coreference cluster node using 'sameAs' edge
                    g.add((rdflib.URIRef(variable_node_uri), coreference.sameAs, rdflib.URIRef(relation_node_uri)))

        return g
    
    def generate_clusters_uris(self):
        """
        USAGE
        generate_cluster_uris(document.coreference_clusters)
        """
        base_uri="http://example.org/cluster/"
        cluster_uris = {}
        for rel in self.coreference_clusters.keys():
            cluster_uri = f"{base_uri}{rel}"
            cluster_uris[rel] = cluster_uri

        return cluster_uris



    def extract_article_namespace(self):
        """
        Extracts and returns the article namespace from the first line of the AMR.
        This is a workaround for the hardcoded IDs generated for the code to work with the amr-ld library
        IDs are in the format 'articleX.sentY' where X and Y are numbers.

        Returns:
            str or None: The extracted article namespace or None if no ID field is found.
        """
        
        # Find the line containing the article ID in the AMR
        
        id_match = re.search(r'# ::id (\S+?)\.', self.sentences[0][2])

        if id_match:
            # Extract and return the article namespace
            article_namespace = id_match.group(1)
            return article_namespace.strip()

        # Return None if no ID field is found
        return None

### Our of class methods
    
def visualize_rdf_graph(rdf_graph, filename="RDF_Visualization.html"):
    # Create a NetworkX graph from RDF
    if isinstance(rdf_graph, str):
        # Parse the N3-formatted string
        graph = rdflib.Graph()
        graph.parse(data=rdf_graph, format="n3")
    else:
        graph = rdf_graph

    nx_graph = nx.Graph()

    for s, p, o in graph:
        nx_graph.add_node(s)
        nx_graph.add_node(o)
        nx_graph.add_edge(s, o, label=p)  # Set the label directly here

    # Create a pyvis network
    nt = Network(height="750px", width="1000px", notebook=True, cdn_resources='remote')
    nt.barnes_hut()

    # Add nodes to the pyvis network
    for node in nx_graph.nodes():
        nt.add_node(node, title=str(node))

    # Add edges to the pyvis network
    for edge in nx_graph.edges(data=True):
        source, target, data = edge
        label = data['label']  # Extract the label from the edge data
        nt.add_edge(source, target, title=str(label))  # Set the title to the label

    nt.show_buttons()
    nt.show(filename)