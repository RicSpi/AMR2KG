#!/usr/bin/python3
import penman
import pickle
from   penman.models.noop import NoOpModel
from   amr_coref.coref.inference import Inference

#  Importing the Document class from parent directory. 
import sys
sys.path.append('..')
from classDocument import Document

def load_amr_graphs(document):
    """
    Load AMR graphs from the Document object.

    Parameters:
        document (Document): An instance of the Document class.

    Returns:
        list: A list of PENAMAN graphs.
    """
    ordered_pgraphs = []

    for _, _, amr_metadata in document.sentences:
        # amr_metadata is the string containing the AMR graph plus ::id and ::snt fields in the document
        graph = penman.decode(amr_metadata, model=NoOpModel())
        ordered_pgraphs.append(graph)

    return ordered_pgraphs


# Simple function to print a list a strings in columns
def print_list_of_strings(items, col_w, max_w):
    cur_len = 0
    fmt = '%%-%ds' % col_w  # ie.. fmt = '%-8s'
    print('  ', end='')
    for item in items:
        print(fmt % item, end='')
        cur_len += 8
        if cur_len > max_w:
            print('\n  ', end='')
            cur_len = 0
    if cur_len != 0:
        print()


if __name__ == '__main__':
    device    = 'cpu'   # 'cuda:0'
    model_dir = 'data/model_coref-v0.1.0/'

    # Load the model and test data
    print('Loading model from %s' % model_dir)
    inference = Inference(model_dir, device=device)

    # Load all_documents from the pickle file
    with open("../all_documents.pickle", 'rb') as file:
        all_documents = pickle.load(file)

    # For testing purposes, let's use the first doccd ument
    document = all_documents[1]

    # Get test data
    print('Loading test data')
    ordered_pgraphs = load_amr_graphs(document)


    # Cluster the data
    # This returns cluster_dict[relation_string] = [(graph_idx, variable), ...]
    print('Clustering')
    cluster_dict = inference.coreference(ordered_pgraphs)
    print()

    # Print out the clusters
    print('Clusters')
    for relation, clusters in cluster_dict.items():
        print(relation)
        cid_strings = ['%d.%s' % (graph_idx, var) for (graph_idx, var) in clusters]
        print_list_of_strings(cid_strings, col_w=8, max_w=120)