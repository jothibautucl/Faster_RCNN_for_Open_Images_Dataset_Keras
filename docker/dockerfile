FROM "ubuntu:latest"
RUN apt-get update && yes | apt-get upgrade
# RUN mkdir -p /tensorflow/models
# RUN apt-get install -y git python-pip
RUN apt-get install python3.8
RUN pip install --upgrade pip
RUN pip install tensorflow-gpu
RUN pip install keras
RUN pip install matplotlib
RUN pip install numpy
RUN pip install open-cv2
RUN pip install pandas
# WORKDIR /tensorflow/models/research
COPY . .