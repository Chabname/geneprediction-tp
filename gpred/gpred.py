import argparse
import sys
import os
import csv
import re


def isfile(path):
    """Check if path is an existing file.
      :Parameters:
          path: Path to the file
    """
    if not os.path.isfile(path):
        if os.path.isdir(path):
            msg = "{0} is a directory".format(path)
        else:
            msg = "{0} does not exist.".format(path)
        raise argparse.ArgumentTypeError(msg)
    return path


def isdir(path):
    """Check if path is an existing file.
      :Parameters:
          path: Path to the file
    """
    if not os.path.isdir(path):
        if os.path.isfile(path):
            msg = "{0} is a file".format(path)
        else:
            msg = "{0} does not exist.".format(path)
        raise argparse.ArgumentTypeError(msg)
    return path


def get_arguments():
    """Retrieves the arguments of the program.
      Returns: An object that contains the arguments
    """
    # Parsing arguments
    parser = argparse.ArgumentParser(description=__doc__, usage=
                                     "{0} -h"
                                     .format(sys.argv[0]))
    parser.add_argument('-i', dest='genome_file', type=isfile, required=True, 
                        help="Complete genome file in fasta format")
    parser.add_argument('-g', dest='min_gene_len', type=int, 
                        default=50, help="Minimum gene length to consider")
    parser.add_argument('-s', dest='max_shine_dalgarno_distance', type=int, 
                        default=16, help="Maximum distance from start codon "
                        "where to look for a Shine-Dalgarno motif")
    parser.add_argument('-d', dest='min_gap', type=int, default=40,
                        help="Minimum gap between two genes (shine box not included).")
    parser.add_argument('-p', dest='predicted_genes_file', type=str, 
                        default=os.curdir + os.sep +"predict_genes.csv",
                        help="Tabular file giving position of predicted genes")
    parser.add_argument('-o', dest='fasta_file', type=str,
                        default=os.curdir + os.sep + "genes.fna",
                        help="Fasta file giving sequence of predicted genes")
    return parser.parse_args()


def read_fasta(fasta_file):
    """Extract the complete genome sequence as a single string
    """
    path = isfile(fasta_file)
    sequence = ""
    with open(path, "r", encoding="utf-8") as file:
        next(file)
        for line in file:
            try:
                sequence += line.strip("\n").upper()
            except StopIteration:
                return
    return sequence

def find_start(start_regex, sequence, start, stop):
    """Find the start codon
    """
    start_index = start_regex.search(sequence, start, stop)
    if start_index != None:
        start_index = start_index.span()[0]
    return start_index


def find_stop(stop_regex, sequence, start):
    """Find the stop codon
    """
    stop_index = stop_regex.search(sequence, start)
    if stop_index != None:
        if (stop_index.span()[0] % 3) == 0:
            stop_index = stop_index.span()[0]
        else:
            stop_index = find_stop(stop_regex, sequence, stop_index.span()[1]+1)
    return stop_index

def has_shine_dalgarno(shine_regex, sequence, start, max_shine_dalgarno_distance):
    """Find a shine dalgarno motif before the start codon
    """
    exist = False

    s_d_index = shine_regex.search(sequence, start - max_shine_dalgarno_distance, len(sequence))

    if s_d_index != None:
        if s_d_index.span()[1] < start - 6:
            exist = True
    return exist
   

def predict_genes(sequence, start_regex, stop_regex, shine_regex, 
                  min_gene_len, max_shine_dalgarno_distance, min_gap):
    """Predict most probable genes
    """
    current_pos = 0
    gene_list = []
    
    while ((len(sequence) - current_pos) >= min_gap):
        current_pos = find_start(start_regex, sequence, current_pos, len(sequence))
        if current_pos is not None:
            stop = find_stop(stop_regex, sequence, current_pos)
            if stop is not None:
                if stop - current_pos >= min_gene_len:
                    if has_shine_dalgarno(shine_regex, sequence, current_pos, max_shine_dalgarno_distance):
                        gene_list.append([current_pos+1, stop + 3])
                        current_pos = stop + 2 + min_gap
                    else:
                        current_pos +=1
                else:
                    current_pos +=1
            else:
                current_pos +=1
    return gene_list



def write_genes_pos(predicted_genes_file, probable_genes):
    """Write list of gene positions
    """
    try:
        with open(predicted_genes_file, "wt") as predict_genes:
            predict_genes_writer = csv.writer(predict_genes, delimiter=",")
            predict_genes_writer.writerow(["Start", "Stop"])
            predict_genes_writer.writerows(probable_genes)
    except IOError:
        sys.exit("Error cannot open {}".format(predicted_genes_file))


def fill(text, width=80):
    """Split text with a line return to respect fasta format"""
    return os.linesep.join(text[i:i+width] for i in range(0, len(text), width))


def write_genes(fasta_file, sequence, probable_genes, sequence_rc, probable_genes_comp):
    """Write gene sequence in fasta format

    """
    try:
        with open(fasta_file, "wt") as fasta:
            for i,gene_pos in enumerate(probable_genes):
                fasta.write(">gene_{0}{1}{2}{1}".format(
                    i+1, os.linesep, 
                    fill(sequence[gene_pos[0]-1:gene_pos[1]])))
            i = i+1
            for j,gene_pos in enumerate(probable_genes_comp):
                fasta.write(">gene_{0}{1}{2}{1}".format(
                            i+1+j, os.linesep,
                            fill(sequence_rc[gene_pos[0]-1:gene_pos[1]])))
    except IOError:
        sys.exit("Error cannot open {}".format(fasta_file))


def reverse_complement(kmer):
    """Get the reverse complement"""
    complement = {'A': 'T', 'C': 'G', 'G': 'C', 'T': 'A'}
    return ''.join([complement[base] for base in kmer[::-1]])


#==============================================================
# Main program
#==============================================================
def main():
    """
    Main program function
    """
    # Gene detection over genome involves to consider a thymine instead of
    # an uracile that we would find on the expressed RNA
    #start_codons = ['TTG', 'CTG', 'ATT', 'ATG', 'GTG']
    #stop_codons = ['TAA', 'TAG', 'TGA']
    start_regex = re.compile('AT[TG]|[ATCG]TG')
    stop_regex = re.compile('TA[GA]|TGA')
    # Shine AGGAGGUAA
    #AGGA ou GGAGG 
    shine_regex = re.compile('A?G?GAGG|GGAG|GG.{1}GG')
    # Arguments
    args = get_arguments()
    # Let us do magic in 5' to 3'
    
    # Don't forget to uncomment !!!
    # Call these function in the order that you want
    sequence = read_fasta(args.genome_file)
    genes_list = predict_genes(sequence, start_regex, 
                stop_regex, shine_regex, args.min_gene_len, 
                args.max_shine_dalgarno_distance, args.min_gap)



    # We reverse and complement
    sequence_rc = reverse_complement(sequence)

    reverse_genes_list = predict_genes(sequence_rc, start_regex, 
                stop_regex, shine_regex, args.min_gene_len, 
                args.max_shine_dalgarno_distance, args.min_gap)

    for i, gene in enumerate(reverse_genes_list):
        gene = [len(sequence) - (gene[1] +1), len(sequence) - (gene[0] +1)]
        reverse_genes_list[i] = gene

    all_genes = genes_list
    all_genes += reverse_genes_list
    
    # Call to output functions
    write_genes_pos(args.predicted_genes_file, all_genes)
    write_genes(args.fasta_file, sequence, genes_list, sequence_rc, reverse_genes_list)



if __name__ == '__main__':
    main()
