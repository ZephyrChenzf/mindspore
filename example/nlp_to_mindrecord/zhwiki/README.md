# Guideline to Convert Training Data zhwiki to MindRecord For Bert Pre Training

<!-- TOC -->

- [What does the example do](#what-does-the-example-do)
- [Run simple test](#run-simple-test)
- [How to use the example to process zhwiki](#how-to-use-the-example-to-process-zhwiki)
    - [Download zhwiki training data](#download-zhwiki-training-data)
    - [Extract the zhwiki](#extract-the-zhwiki)
    - [Generate MindRecord](#generate-mindrecord)
    - [Create MindDataset By MindRecord](#create-minddataset-by-mindrecord)


<!-- /TOC -->

## What does the example do

This example is based on [zhwiki](https://dumps.wikimedia.org/zhwiki) training data, generating MindRecord file, and finally used for Bert network training.

1.  run.sh: generate MindRecord entry script.
2.  run_read.py: create MindDataset by MindRecord entry script.
    - create_dataset.py: use MindDataset to read MindRecord to generate dataset.

## Run simple test

Follow the step:

```bash
bash run_simple.sh         # generate output/simple.mindrecord* by ../../../third_party/to_mindrecord/zhwiki/sample_text.txt
bash run_read_simple.sh    # use MindDataset to read output/simple.mindrecord*
```

## How to use the example to process zhwiki

Download zhwiki data, extract it, convert it to MindRecord, use MindDataset to read MindRecord.

### Download zhwiki training data

> [zhwiki dataset download address](https://dumps.wikimedia.org/zhwiki) **-> 20200401 -> zhwiki-20200401-pages-articles-multistream.xml.bz2**

- put the zhwiki-20200401-pages-articles-multistream.xml.bz2 in {your-mindspore}/example/nlp_to_mindrecord/zhwiki/data directory.

### Extract the zhwiki

1. Download [wikiextractor](https://github.com/attardi/wikiextractor) script to {your-mindspore}/example/nlp_to_mindrecord/zhwiki/data directory.

    ```
    $ ls data/
    README.md  wikiextractor  zhwiki-20200401-pages-articles-multistream.xml.bz2
    ```

2. Extract the zhwiki.
    ```python
    python data/wikiextractor/WikiExtractor.py data/zhwiki-20200401-pages-articles-multistream.xml.bz2 --processes 4 --templates data/template --bytes 8M --min_text_length 0 --filter_disambig_pages --output data/extract
    ```

3. Generate like this:
    ```
    $ ls data/extract
    AA AB
    ```

### Generate MindRecord

1. Run the run.sh script.
    ```
    bash run.sh
    ```
    > Caution: This process maybe slow, please wait patiently. If you do not have a machine with enough memory and cpu, it is recommended that you modify the script to generate mindrecord in step by step.

2. The output like this:
    ```
    patching file create_pretraining_data_patched.py (read from create_pretraining_data.py)
    Begin preprocess input file: ./data/extract/AA/wiki_00
    Begin output file: AAwiki_00.mindrecord
    Total task: 5, processing: 1
    Begin preprocess input file: ./data/extract/AA/wiki_01
    Begin output file: AAwiki_01.mindrecord
    Total task: 5, processing: 2
    Begin preprocess input file: ./data/extract/AA/wiki_02
    Begin output file: AAwiki_02.mindrecord
    Total task: 5, processing: 3
    Begin preprocess input file: ./data/extract/AB/wiki_02
    Begin output file: ABwiki_02.mindrecord
    Total task: 5, processing: 4
    ...
    ```

3. Generate files like this:
    ```bash
    $ ls output/
    AAwiki_00.mindrecord AAwiki_00.mindrecord.db AAwiki_01.mindrecord AAwiki_01.mindrecord.db AAwiki_02.mindrecord AAwiki_02.mindrecord.db ... ABwiki_00.mindrecord ABwiki_00.mindrecord.db ...
    ```

### Create MindDataset By MindRecord

1. Run the run_read.sh script.
    ```bash
    bash run_read.sh
    ```

2. The output like this:
    ```
    ...
    example 74: input_ids: [  101  8168   118 12847  8783  9977 15908   117  8256  9245 11643  8168  8847  8588 11575  8154  8228   143  8384  8376  9197 10241   103 10564 11421  8199 12268   112   161  8228 11541  9586  8436  8174  8363  9864  9702   103   103   119   103  9947 10564   103  8436  8806 11479   103  8912   119   103   103   103 12209  8303   103  8757  8824   117  8256   103  8619  8168 11541   102 11684  8196   103  8228  8847 11523   117  9059  9064 12410  8358  8181 10764   117 11167 11706  9920   148  8332 11390  8936  8205 10951 11997   103  8154   117   103  8670 10467   112   161 10951 13139 12413   117 10288   143 10425  8205   152 10795  8472  8196   103   161 12126  9172 13129 12106  8217  8174 12244  8205   143   103  8461  8277 10628   160  8221   119   102]
    example 74: input_mask: [1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1]
    example 74: segment_ids: [0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1]
    example 74: masked_lm_positions: [  6  22  37  38  40  43  47  50  51  52  55  60  67  76  89  92  98 109 120   0]
    example 74: masked_lm_ids: [ 8118  8165  8329  8890  8554  8458   119  8850  8565 10392  8174 11467  10291  8181  8549 12718 13139   112   158     0]
    example 74: masked_lm_weights: [1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 1. 0.]
    example 74: next_sentence_labels: [0]
    ...
    ```
