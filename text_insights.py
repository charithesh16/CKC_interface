import spacy
import networkx as nx
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from wordcloud import WordCloud
from collections import Counter
import numpy as np
from itertools import tee


def get_sentences(data, country=None, province=None, district=None):
    """Extract sentences from the data hierarchy based on location filters."""
    if district:
        articles = data[country][province][district]["articles"] + data[country]["emptyLocations"]
    elif province:
        articles = data[country][province]["articles"] + data[country]["emptyLocations"]
    else:
        articles = data[country]["articles"]
    return (article["sentence"] for article in articles)  # Return a generator for efficiency


def generate_bigrams(sentences, nlp):
    """Generate bigrams from sentences using spaCy for tokenization."""
    def pairwise(iterable):
        a, b = tee(iterable)
        next(b, None)
        return zip(a, b)

    for sentence in sentences:
        doc = nlp(sentence.lower())
        tokens = (token.text for token in doc if not token.is_stop and not token.is_punct)
        yield from pairwise(tokens)  # Yield bigrams as they're generated

def get_word_graph(original_data, country=None, province=None, district=None, threshold=0):
    """Build and visualize a bigram graph, limited to the top 30 words."""
    # Extract sentences and load SpaCy model
    sentences = get_sentences(original_data, country, province, district)
    sentences_list = []
    for sentence in sentences:
        sentences_list.append(sentence)
    sentences = sentences_list
    nlp = spacy.load('en_core_web_sm', disable=['parser', 'ner'])  # Disable unused components for speed

    # Generate bigrams and count frequencies
    generate_word_cloud(sentences)
    bigrams = generate_bigrams(sentences, nlp)
    bigram_count = Counter(bigrams)

    # Filter bigrams based on the frequency threshold
    filtered_bigrams = [(a, b, weight) for (a, b), weight in bigram_count.items() if weight >= threshold]

    # Sort by weight and take the top 30 bigrams
    top_bigrams = sorted(filtered_bigrams, key=lambda x: x[2], reverse=True)[:30]

    # Create and populate the graph
    G = nx.Graph()
    G.add_weighted_edges_from(top_bigrams)

    if not G.edges:
        print("No edges meet the threshold.")
        return

    # Define graph layout
    pos = nx.spring_layout(G, k=2.5, iterations=20)

    # Normalize edge widths for visualization
    edges = G.edges(data=True)
    weights = np.array([data['weight'] for _, _, data in edges])
    scaled_widths = (weights / weights.max()) * 3 if weights.size > 0 else []

    # Plot the graph
    plt.figure(figsize=(10, 10))
    nx.draw_networkx_nodes(G, pos, node_color='skyblue', node_size=500)
    nx.draw_networkx_edges(G, pos, edgelist=edges, width=scaled_widths, alpha=0.7, edge_color='grey')
    nx.draw_networkx_labels(G, pos, font_size=7, font_family='sans-serif')
    plt.title('Bigram Network from Sentences (Top 30)')
    plt.axis('off')
    image_path = "static/graph.png"  # Save the image in the static folder
    plt.savefig(image_path)
    plt.close()  # Close the plot to free memory
    return image_path

    # plt.show()
def generate_word_cloud(sentences, output_path="static/wordcloud.png"):
    """Generate a word cloud from sentences and save as an image."""
    # Combine all sentences into a single string
    sentences_list = []
    for sentence in sentences:
        sentences_list.append(sentence)
    text = " ".join(sentences_list)

    # Generate the word cloud
    wordcloud = WordCloud(width=800, height=400, background_color="white").generate(text)

    # Save the word cloud image
    plt.figure(figsize=(10, 5))
    plt.imshow(wordcloud, interpolation="bilinear")
    plt.axis("off")
    plt.tight_layout(pad=0)
    plt.savefig(output_path)
    plt.close()


# Example Usage
# get_word_graph(data, country='example_country', threshold=10)
# data = ...  # Load your hierarchical data
