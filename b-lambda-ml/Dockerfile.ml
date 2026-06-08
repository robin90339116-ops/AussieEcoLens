FROM public.ecr.aws/lambda/python:3.12

WORKDIR ${LAMBDA_TASK_ROOT}

COPY requirements-lambda.txt .

# Install CPU-only torch/torchvision first to keep the image small and avoid CUDA wheels.
RUN python -m pip install --upgrade pip && \
    python -m pip install --no-cache-dir \
        torch==2.12.0 torchvision==0.27.0 \
        --index-url https://download.pytorch.org/whl/cpu && \
    python -m pip install --no-cache-dir -r requirements-lambda.txt && \
    # megadetector pulls in opencv-python (needs libGL). Replace it with the
    # headless build so the Lambda runtime has no libGL.so.1 dependency.
    python -m pip uninstall -y opencv-python || true && \
    python -m pip install --no-cache-dir --force-reinstall --no-deps opencv-python-headless==4.13.0.92

COPY ecolens_core.py ml_lambda.py labels.txt mdv5a.pt model.pt ./

ENV MD_MODEL_PATH=${LAMBDA_TASK_ROOT}/mdv5a.pt
ENV SPECIES_MODEL_PATH=${LAMBDA_TASK_ROOT}/model.pt
ENV LABELS_PATH=${LAMBDA_TASK_ROOT}/labels.txt

CMD ["ml_lambda.lambda_handler"]
