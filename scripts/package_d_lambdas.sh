#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${ROOT_DIR}/build/d-lambda-packages"
DIST_DIR="${ROOT_DIR}/build/d-lambda-zips"
PYTHON_BIN="${PYTHON_BIN:-python3}"

rm -rf "${BUILD_DIR}" "${DIST_DIR}"
mkdir -p "${BUILD_DIR}" "${DIST_DIR}"

package_lambda() {
  local name="$1"
  local handler_dir="$2"
  local requirements_file="$3"
  local stage_dir="${BUILD_DIR}/${name}"

  mkdir -p "${stage_dir}"
  cp -R "${ROOT_DIR}/lambda/shared/." "${stage_dir}/"
  cp -R "${ROOT_DIR}/${handler_dir}/." "${stage_dir}/"
  find "${stage_dir}" -type d -name "__pycache__" -prune -exec rm -rf {} +

  if [[ -f "${requirements_file}" ]]; then
    "${PYTHON_BIN}" -m pip install -r "${requirements_file}" -t "${stage_dir}" >/dev/null
  fi

  (
    cd "${stage_dir}"
    zip -qr "${DIST_DIR}/${name}.zip" .
  )
  echo "created ${DIST_DIR}/${name}.zip"
}

package_lambda "q3_thumbnail_lookup" "lambda/queries-aws/q3_thumbnail_lookup" "${ROOT_DIR}/lambda/queries-aws/requirements.txt"
package_lambda "q4_image_search" "lambda/queries-aws/q4_image_search" "${ROOT_DIR}/lambda/queries-aws/requirements.txt"
package_lambda "q5_update_tags" "lambda/queries-aws/q5_update_tags" "${ROOT_DIR}/lambda/queries-aws/requirements.txt"
package_lambda "q6_delete_file" "lambda/queries-aws/q6_delete_file" "${ROOT_DIR}/lambda/queries-aws/requirements.txt"
package_lambda "notifications" "lambda/notifications" "${ROOT_DIR}/lambda/notifications/requirements.txt"

echo "D group Lambda packages are in ${DIST_DIR}"
