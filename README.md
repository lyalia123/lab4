# Mini MapReduce Lab — Amazon EMR

## Description
This repository contains the MapReduce pipeline for the Mini-MapReduce lab on Amazon EMR. 
The job counts word frequencies in a sample Wikipedia dataset (`corpus.txt`) using Python mapper and reducer scripts.

## Files
- `mapper.py` — Mapper script that emits each word with a count of 1.
- `reducer.py` — Reducer script that sums counts for each word.
- `README.md` — This file.
- `corpus.txt` — Sample dataset (Simple English Wikipedia dump).

## Dataset
The dataset is a small sample from the Simple English Wikipedia:
- Source: [https://github.com/LGDoor/Dump-of-Simple-English-Wiki](https://github.com/LGDoor/Dump-of-Simple-English-Wiki)
- The file used: `corpus.txt`

## How to Run

1. **Upload dataset to HDFS:**
hdfs dfs -mkdir -p /user/hadoop/input
hdfs dfs -put corpus.txt /user/hadoop/input/
Remove old output directory (if exists):

hdfs dfs -rm -r /user/hadoop/output


Run Hadoop Streaming job:

hadoop jar /usr/lib/hadoop-mapreduce/hadoop-streaming.jar \
  -files mapper.py,reducer.py \
  -input /user/hadoop/input/ \
  -output /user/hadoop/output/ \
  -mapper mapper.py \
  -reducer reducer.py


Check output:

hdfs dfs -ls /user/hadoop/output/
hdfs dfs -cat /user/hadoop/output/part-00000 | head


The output files (part-00000, part-00001, etc.) will contain word counts.

Notes

Ensure the scripts are executable:

chmod +x mapper.py reducer.py
