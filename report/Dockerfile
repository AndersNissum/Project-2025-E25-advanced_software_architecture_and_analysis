# Use the base Ubuntu image
FROM ubuntu:latest

# Set environment variables to non-interactive (this prevents build prompts)
ENV DEBIAN_FRONTEND=noninteractive

# Install all necessary LaTeX packages to support your preamble
RUN apt-get update -q && \
    apt-get install -yq texlive texlive-xetex texlive-science \
                       texlive-latex-extra texlive-pictures texlive-fonts-extra \
                       biber && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
COPY ./latexUtils/compile.sh .
RUN sed -i 's/\r$//' compile.sh
RUN chmod +x compile.sh
ENTRYPOINT ["bash", "compile.sh"]
