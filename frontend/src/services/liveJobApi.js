const API_BASE_URL =
  `${import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"}/api/v1`;
// const API_BASE_URL = "/api/v1";

async function request(
  url,
  options = {}
) {
  const response = await fetch(
    url,
    options
  );

  let data = null;

  try {
    data = await response.json();
  } catch {
    data = null;
  }

  if (!response.ok) {

    const message =
      data?.detail ||
      data?.message ||
      `Request failed with status ${response.status}`;

    throw new Error(
      message
    );
  }

  return data;
}


export async function findFreshJobs(
  profileId
) {

  return request(
    `${API_BASE}/live-jobs/search/${Number(
      profileId
    )}`,
    {
      method: "POST",
    }
  );
}