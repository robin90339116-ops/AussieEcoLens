# Report Snippets For ZHU WENXUAN

## Team Report Contribution Table Entry

**Name and ID:** ZHU WENXUAN, 35371811  
**Contribution:** [Adjust percentage with team agreement]  
**Elements contributed:** Implemented the Lambda + ML module for the Aussie EcoLens platform. This included refactoring the provided batch ML script into reusable functions, creating the thumbnail generation Lambda, building the species-tagging inference (MegaDetector + SpeciesNet) as a containerised service deployed on Oracle Cloud with a lightweight AWS S3-triggered Lambda, designing the metadata JSON contract for database integration, adding cross-cloud token authentication, preparing deployment documentation, and validating real inference output across multiple species using the test images.

## Individual Report: Role And Contribution (Approx. 150 Words)

My role in the project was to implement the Lambda + ML component of the multi-cloud wildlife observation platform. I converted the original batch-processing model script into reusable Python functions usable from both serverless handlers and a long-running service. I implemented a thumbnail generator that preserves aspect ratio and compresses images, and I built the species-tagging inference (MegaDetector + SpeciesNet) as a containerised FastAPI service deployed on Oracle Cloud, because the model container is large and AWS Academy limits a heavy Lambda. To keep the upload event serverless, a lightweight AWS Lambda is triggered by S3 and forwards a presigned URL and bearer token to the Oracle service. I defined the metadata output contract used by the database and frontend modules, added cross-cloud token authentication, and verified real inference across multiple species. I also prepared Docker, docker-compose, systemd, and deployment documentation for the team.

## Individual Report: Teamwork Reflection (Approx. 150 Words)

The teamwork experience showed me that a cloud application is difficult mainly because every module depends on clear contracts with other modules. My part depended on the upload bucket and S3 events from the authentication/API member, while the database and frontend members depended on my metadata fields being stable. A key challenge was that ML inference is much heavier than normal serverless code, so I had to communicate early that a container-based Lambda was more realistic than a zip deployment. The team also needed to balance implementation depth with demo reliability, because the marking rubric rewards working end-to-end features rather than isolated code. I learned that documenting assumptions, field names and error responses is as important as writing the Lambda itself. Overall, the team worked more effectively when we treated integration as a shared responsibility rather than assuming each member's component would connect automatically at the end.

## Demo Q&A Preparation

**Why run the ML on Oracle Cloud instead of AWS Lambda?**  
The ML container is large (PyTorch plus two model files), and AWS Academy imposes IAM role and container limitations that make a heavy Lambda risky. I deployed the inference as a FastAPI service on an Oracle Cloud (OCI) instance, while keeping a lightweight AWS Lambda triggered by the S3 upload event. This satisfies the "upload triggers a serverless function" requirement, strengthens the multi-cloud architecture (AWS Cognito/S3 + Oracle compute + GCP database), and avoids cold-start and size limits. The assignment only mandates AWS Cognito for authentication; other services may run on a secondary cloud.

**How does the cross-cloud call stay secure?**  
The S3-triggered AWS Lambda generates a short-lived presigned GET URL and calls the OCI endpoint over HTTPS with a bearer token. The OCI service validates the token before running inference. The design isolates token validation so it can be upgraded from a shared secret to full Cognito JWT verification.

**Why use a Lambda container for ML tagging (Route A alternative)?**  
If deploying on AWS instead, the model files and PyTorch dependencies are large, so a container image deployed through ECR is more suitable than a zip Lambda package. It also keeps the runtime environment consistent for demo and deployment.

**How does your module support future model updates?**  
Model paths are configured through environment variables, and the inference logic is separated from the Lambda handler. A new model can be packaged into a new container image or referenced by a new path without rewriting the API contract.

**How does thumbnail generation meet the rubric?**  
The thumbnail helper preserves aspect ratio, compresses to JPEG, and writes a smaller preview file. Local evidence shows three test images were reduced to around 0.52%-5.57% of their original sizes.

**Have you verified the ML model actually works?**  
Yes. I ran the full MegaDetector + SpeciesNet pipeline locally on CPU across 8 species in `test_images`. All were classified correctly (7 at 100% confidence, 1 at 99.2%). `Bos_taurus_1.JPG` returned a count of 6 cattle, which confirms multi-instance tag counting needed by the AND/min-count queries. Results are saved in `test_results/REAL_INFERENCE_RESULTS.md`.

**Why is onnx2torch a dependency?**  
The SpeciesNet `model.pt` was exported through onnx2torch, so the Lambda container must include onnx2torch and onnx to unpickle and run the model. I documented this in the deployment guide after hitting and resolving the `ModuleNotFoundError` during testing.

**What metadata do you give to the database module?**  
The ML Lambda returns `file_id`, `file_type`, `original_url`, `thumbnail_url`, `checksum`, `tags`, `predictions`, and `created_at`. This supports tag queries, thumbnail-to-original lookup and future auditability.
