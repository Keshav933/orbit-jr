// const API_BASE_URL = "/api/v1";
const API_BASE_URL =
  `${import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"}/api/v1`;

async function handleResponse(response) {
  if (!response.ok) {
    let message = "Request failed";
    try {
      const data = await response.json();
      if (data.detail) {
        message = data.detail;
      }
    } catch {
      // Keep default error.
    }
    throw new Error(message);
  }
  return response.json();
}

export async function getHealth() {
  const response = await fetch(
    `${API_BASE_URL}/health`
  );
  return handleResponse(response);
}

export async function getUsers() {
  const response = await fetch(
    `${API_BASE_URL}/users`
  );
  return handleResponse(response);
}

export async function getRecommendations(
  profileId,
  topK = 20,
  filters = {},
  page = 1,
  pageSize = 20
) {
  const params = new URLSearchParams();

  params.set(
    "top_k",
    String(topK)
  );

  params.set(
    "page",
    String(page)
  );

  params.set(
    "page_size",
    String(pageSize)
  );

  if (filters.search?.trim()) {
    params.set(
      "search",
      filters.search.trim()
    );
  }

  if (filters.location?.trim()) {
    params.set(
      "location",
      filters.location.trim()
    );
  }

  if (filters.role?.trim()) {
    params.set(
      "role",
      filters.role.trim()
    );
  }

  if (filters.remoteOnly) {
    params.set(
      "remote_only",
      "true"
    );
  }

  if (
    Number(filters.minScore || 0) > 0
  ) {
    params.set(
      "min_score",
      String(
        Number(filters.minScore) / 100
      )
    );
  }

  if (filters.experienceLevel) {
    params.set(
      "experience_level",
      filters.experienceLevel
    );
  }

  if (filters.employmentType) {
    params.set(
      "employment_type",
      filters.employmentType
    );
  }

  params.set(
    "sort_by",
    filters.sortBy || "recent"
  );

  const response = await fetch(
    `${API_BASE_URL}/recommendations/${profileId}?${params.toString()}`
  );

  return handleResponse(response);
}

export async function getAllRecommendations(
  profileId,
  filters = {},
  topK = 100
) {
  return getRecommendations(
    profileId,
    topK,
    filters,
    1,
    topK
  );
}

export async function getJobDetails(
  jobId
) {
  const response = await fetch(
    `${API_BASE_URL}/jobs/${jobId}`
  );

  return handleResponse(response);
}

export async function getSavedJobIds(
  profileId
) {
  const response = await fetch(
    `${API_BASE_URL}/saved-jobs/${profileId}/ids`
  );

  return handleResponse(response);
}

export async function getSavedJobs(
  profileId
) {
  const response = await fetch(
    `${API_BASE_URL}/saved-jobs/${profileId}`
  );

  return handleResponse(response);
}

export async function saveJob(
  profileId,
  jobId
) {
  const response = await fetch(
    `${API_BASE_URL}/saved-jobs/${profileId}/${jobId}`,
    {
      method: "POST",
    }
  );

  return handleResponse(response);
}

export async function removeSavedJob(
  profileId,
  jobId
) {
  const response = await fetch(
    `${API_BASE_URL}/saved-jobs/${profileId}/${jobId}`,
    {
      method: "DELETE",
    }
  );

  return handleResponse(response);
}

export async function onboardCandidate(
  candidateData
) {
  const formData = new FormData();

  formData.append(
    "full_name",
    candidateData.full_name
  );

  formData.append(
    "email",
    candidateData.email
  );

  formData.append(
    "education",
    candidateData.education
  );

  formData.append(
    "experience_years",
    candidateData.experience_years
  );

  formData.append(
    "location",
    candidateData.location
  );

  formData.append(
    "preferred_role",
    candidateData.preferred_role
  );

  formData.append(
    "summary",
    candidateData.summary
  );

  formData.append(
    "resume",
    candidateData.resume
  );

  const response = await fetch(
    `${API_BASE_URL}/candidates/onboard`,
    {
      method: "POST",
      body: formData,
    }
  );

  return handleResponse(response);
}