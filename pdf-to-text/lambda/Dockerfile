FROM public.ecr.aws/lambda/python:3.12

# Copy and install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy function code
COPY app.py .

# Command for Lambda runtime
CMD ["app.lambda_handler"]
