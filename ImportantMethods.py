def title2Namespace(Document):
    """
    Input a documents, returns document Namespace ready title
    """
    title = Document.title.replace('=','')
    title = title.replace(' ','')
    return title

def triples_extractor(Document):
    """
    input  = a Document object
    output = a list of penman graphs per sentence
    """
    # Keep in mind that penman.decode returns a Graph() object!!
    triples = [penman.decode(sentence[1]) for sentence in Document.sentences]
    
    return triples
