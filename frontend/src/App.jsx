import { findFreshJobs } from "./services/liveJobApi";
import "./liveSearchStyles.css";
import {
  Fragment,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  getHealth,
  getRecommendations,
  getJobDetails,
  getSavedJobIds,
  getSavedJobs,
  saveJob,
  removeSavedJob,
  onboardCandidate,
} from "./services/api";
import "./styles.css";
import "./jobUxOverrides.css";
const PROFILE_STORAGE_KEY =
  "orbit_jr_profile_id";
const SKILLS_STORAGE_KEY =
  "orbit_jr_profile_skills";
const DEFAULT_FILTERS = {
  search: "",
  location: "",
  role: "",
  remoteOnly: false,
  minScore: 0,
  experienceLevel: "",
  employmentType: "",
  sortBy: "recent",
};
function formatScore(score) {
  const value = Number(score || 0);
  return `${Math.round(value * 100)}%`;
}
function cleanText(text) {
  if (!text) {
    return "";
  }
  return String(text)
    .replaceAll("&amp;", "&")
    .replaceAll("&quot;", '"')
    .replaceAll("&#39;", "'")
    .replaceAll("&lt;", "<")
    .replaceAll("&gt;", ">");
}
function getSourceLabel(sourceType) {
  const labels = {
    jobicy: "Jobicy",
    himalayas: "Himalayas",
    remoteok: "Remote OK",
  };
  return labels[sourceType] || "Personalized recommendation";
}
function SkillTag({
  children,
  type = "normal",
}) {
  return (
    <span
      className={`skill-tag ${type}`}
    >
      {cleanText(children)}
    </span>
  );
}
/* =========================================================
   ONBOARDING
\========================================================= */
function OnboardingForm({
  onCompleted,
}) {
  const [form, setForm] = useState({
    full_name: "",
    email: "",
    education: "B.Tech Computer Science",
    experience_years: "0",
    location: "",
    preferred_role: "Software Developer",
    summary: "",
  });
  const [resume, setResume] =
    useState(null);
  const [loading, setLoading] =
    useState(false);
  const [error, setError] =
    useState("");
  function handleChange(event) {
    const {
      name,
      value,
    } = event.target;
    setForm((current) => ({
      ...current,
      [name]: value,
    }));
  }
  function handleResumeChange(event) {
    const file =
      event.target.files?.[0] || null;
    setResume(file);
    setError("");
    if (!file) {
      return;
    }
    if (
      !file.name
        .toLowerCase()
        .endsWith(".pdf")
    ) {
      setResume(null);
      setError(
        "Please upload a PDF resume."
      );
    }
  }
  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    if (!form.full_name.trim()) {
      setError(
        "Please enter your name."
      );
      return;
    }
    if (!form.email.trim()) {
      setError(
        "Please enter your email."
      );
      return;
    }
    if (!resume) {
      setError(
        "Please upload your PDF resume."
      );
      return;
    }
    setLoading(true);
    try {
      const data =
        await onboardCandidate({
          ...form,
          experience_years:
            form.experience_years || "0",
          resume,
        });
      onCompleted(data);
    } catch (err) {
      setError(
        err.message ||
        "Could not process your resume."
      );
    } finally {
      setLoading(false);
    }
  }
  return (
    <div className="onboarding-page">
      <div className="onboarding-card">
        <div className="onboarding-intro">
          <p className="eyebrow">
            ORBIT-JR
          </p>
          <h1>
            Find jobs that fit you.
          </h1>
          <p>
            Upload your resume and tell us a
            little about yourself. ORBIT-JR will
            extract your skills and build your
            personalized job recommendations.
          </p>
        </div>
        {error && (
          <div className="error-box">
            <strong>
              Could not build your profile
            </strong>
            <p>
              {error}
            </p>
          </div>
        )}
        <form
          className="onboarding-form"
          onSubmit={handleSubmit}
        >
          <div className="form-grid">
            <div className="form-group">
              <label htmlFor="full_name">
                Full name
              </label>
              <input
                id="full_name"
                name="full_name"
                type="text"
                value={form.full_name}
                onChange={handleChange}
                placeholder="Your full name"
                required
              />
            </div>
            <div className="form-group">
              <label htmlFor="email">
                Email
              </label>
              <input
                id="email"
                name="email"
                type="email"
                value={form.email}
                onChange={handleChange}
                placeholder="you@example.com"
                required
              />
            </div>
            <div className="form-group full">
              <label htmlFor="education">
                Education
              </label>
              <input
                id="education"
                name="education"
                type="text"
                value={form.education}
                onChange={handleChange}
                placeholder="B.Tech Computer Science"
              />
            </div>
            <div className="form-group">
              <label htmlFor="experience_years">
                Experience
              </label>
              <input
                id="experience_years"
                name="experience_years"
                type="number"
                min="0"
                max="50"
                step="0.1"
                value={form.experience_years}
                onChange={handleChange}
              />
            </div>
            <div className="form-group">
              <label htmlFor="location">
                Preferred location
              </label>
              <input
                id="location"
                name="location"
                type="text"
                value={form.location}
                onChange={handleChange}
                placeholder="Delhi, Bengaluru, Remote..."
              />
            </div>
            <div className="form-group full">
              <label htmlFor="preferred_role">
                Preferred role
              </label>
              <input
                id="preferred_role"
                name="preferred_role"
                type="text"
                value={form.preferred_role}
                onChange={handleChange}
                placeholder="Software Developer"
              />
            </div>
            <div className="form-group full">
              <label htmlFor="summary">
                Short profile summary
              </label>
              <textarea
                id="summary"
                name="summary"
                value={form.summary}
                onChange={handleChange}
                placeholder="Tell us briefly about your interests, projects or career goals."
                rows="4"
              />
            </div>
            <div className="form-group full">
              <label htmlFor="resume">
                Resume PDF
              </label>
              <div className="resume-upload">
                <input
                  id="resume"
                  type="file"
                  accept=".pdf,application/pdf"
                  onChange={
                    handleResumeChange
                  }
                />
                {resume && (
                  <p className="file-name">
                    Selected: {resume.name}
                  </p>
                )}
              </div>
            </div>
          </div>
          <button
            type="submit"
            className="primary-neu-button"
            disabled={loading}
          >
            {loading
              ? "Building your recommendations..."
              : "Build My Recommendations"}
          </button>
        </form>
      </div>
    </div>
  );
}
/* =========================================================
   FILTER PANEL
\========================================================= */
function FilterPanel({
  filters,
  onChange,
  onApply,
  onClear,
  loading,
}) {
  const activeFilterCount =
    [
      filters.search,
      filters.location,
      filters.role,
      filters.remoteOnly,
      Number(filters.minScore) > 0,
      filters.experienceLevel,
      filters.employmentType,
    ].filter(Boolean).length;
  function handleInputChange(event) {
    const {
      name,
      value,
      type,
      checked,
    } = event.target;
    onChange({
      ...filters,
      [name]:
        type === "checkbox"
          ? checked
          : value,
    });
  }
  return (
    <section className="filter-panel">
      <div className="filter-heading">
        <div>
          <p className="eyebrow">
            REFINE RESULTS
          </p>
          <h2>
            Find the right opportunity
          </h2>
        </div>
        <span className="filter-count">
          {activeFilterCount} active
        </span>
      </div>
      <div className="filter-grid">
        <div className="filter-group">
          <label htmlFor="filter-search">
            Search
          </label>
          <input
            id="filter-search"
            name="search"
            type="text"
            value={filters.search}
            onChange={handleInputChange}
            placeholder="Job title or company"
          />
        </div>
        <div className="filter-group">
          <label htmlFor="filter-location">
            Location
          </label>
          <input
            id="filter-location"
            name="location"
            type="text"
            value={filters.location}
            onChange={handleInputChange}
            placeholder="Mumbai, Delhi..."
          />
        </div>
        <div className="filter-group">
          <label htmlFor="filter-role">
            Role / category
          </label>
          <input
            id="filter-role"
            name="role"
            type="text"
            value={filters.role}
            onChange={handleInputChange}
            placeholder="Software, Data..."
          />
        </div>
        <div className="filter-group">
          <label htmlFor="filter-experience">
            Experience
          </label>
          <select
            id="filter-experience"
            name="experienceLevel"
            value={filters.experienceLevel}
            onChange={handleInputChange}
          >
            <option value="">
              Any experience
            </option>
            <option value="entry">
              Entry level
            </option>
            <option value="junior">
              Junior
            </option>
            <option value="mid">
              Mid level
            </option>
            <option value="senior">
              Senior
            </option>
          </select>
        </div>
        <div className="filter-group">
          <label htmlFor="filter-employment">
            Employment
          </label>
          <select
            id="filter-employment"
            name="employmentType"
            value={filters.employmentType}
            onChange={handleInputChange}
          >
            <option value="">
              Any type
            </option>
            <option value="full">
              Full-time
            </option>
            <option value="part">
              Part-time
            </option>
            <option value="intern">
              Internship
            </option>
            <option value="contract">
              Contract
            </option>
          </select>
        </div>
        <div className="filter-group">
          <label htmlFor="filter-sort">
            Sort by
          </label>
          <select
            id="filter-sort"
            name="sortBy"
            value={filters.sortBy}
            onChange={handleInputChange}
          >
            <option value="best_match">
              Best match
            </option>
            <option value="skill_match">
              Highest skill match
            </option>
            <option value="recent">
              Most recent
            </option>
          </select>
        </div>
        <div className="filter-group range-group">
          <div className="range-header">
            <label htmlFor="filter-score">
              Minimum match
            </label>
            <strong>
              {filters.minScore}%
            </strong>
          </div>
          <input
            id="filter-score"
            name="minScore"
            type="range"
            min="0"
            max="100"
            step="5"
            value={filters.minScore}
            onChange={handleInputChange}
          />
        </div>
        <label className="remote-control">
          <input
            name="remoteOnly"
            type="checkbox"
            checked={filters.remoteOnly}
            onChange={handleInputChange}
          />
          <span>
            Remote jobs only
          </span>
        </label>
      </div>
      <div className="filter-actions">
        <button
          className="primary-neu-button small"
          onClick={onApply}
          disabled={loading}
        >
          {loading
            ? "Searching..."
            : "Apply Filters"}
        </button>
        <button
          className="secondary-neu-button"
          onClick={onClear}
          disabled={loading}
        >
          Clear
        </button>
      </div>
    </section>
  );
}
/* =========================================================
   JOB CARD
\========================================================= */
function JobCard({
  job,
  isSaved,
  onViewDetails,
  onSave,
}) {
  const matchedSkills =
    job.matched_skills || [];
  const requiredGaps =
    job.required_gaps || [];
  const preferredGaps =
    job.preferred_gaps || [];
  return (
    <article className="job-card">
      <div className="job-card-header">
        <div className="job-title-area">
          <div className="job-title-row">
            <h2>
              {cleanText(job.title)}
            </h2>
            {job.is_remote && (
              <span className="remote-badge">
                Remote
              </span>
            )}
          </div>
          <p className="company">
            {cleanText(
              job.company_name ||
              "Company not available"
            )}
          </p>
          <p className="location">
            {cleanText(
              job.location ||
              "Location not available"
            )}
          </p>
          {job.posted_date && (
            <p className="posted-date">
              Posted: {String(job.posted_date)}
            </p>
          )}
        </div>
        <div className="score-box">
          <span className="score-label">
            Match
          </span>
          <strong>
            {formatScore(
              job.final_score
            )}
          </strong>
        </div>
      </div>
      <div className="job-stats">
        <div>
          <span>
            Skills matched
          </span>
          <strong>
            {job.matched_skill_count || 0}
          </strong>
        </div>
        <div>
          <span>
            Job skills
          </span>
          <strong>
            {job.total_job_skills || 0}
          </strong>
        </div>
        <div>
          <span>
            Confidence
          </span>
          <strong>
            {formatScore(
              job.confidence
            )}
          </strong>
        </div>
      </div>
      <section className="job-section">
        <h3>
          Why it matches
        </h3>
        {matchedSkills.length > 0 ? (
          <div className="skill-list">
            {matchedSkills.map(
              (skill) => (
                <SkillTag
                  key={skill.skill_id}
                  type="matched"
                >
                  {skill.skill_name}
                </SkillTag>
              )
            )}
          </div>
        ) : (
          <p className="muted">
            No direct skill matches found.
          </p>
        )}
      </section>
      <section className="job-section">
        <h3>
          Required skills to improve
        </h3>
        {requiredGaps.length > 0 ? (
          <div className="skill-list">
            {requiredGaps
              .slice(0, 8)
              .map((skill) => (
                <SkillTag
                  key={skill.skill_id}
                  type="required-gap"
                >
                  {skill.skill_name}
                </SkillTag>
              ))}
          </div>
        ) : (
          <p className="success-text">
            No detected required skill gaps.
          </p>
        )}
      </section>
      {preferredGaps.length > 0 && (
        <section className="job-section">
          <h3>
            Preferred skills
          </h3>
          <div className="skill-list">
            {preferredGaps
              .slice(0, 6)
              .map((skill) => (
                <SkillTag
                  key={skill.skill_id}
                  type="preferred-gap"
                >
                  {skill.skill_name}
                </SkillTag>
              ))}
          </div>
        </section>
      )}
      <div className="job-footer">
        <span className="source-text">
          {job.source_type
            ? `Source: ${getSourceLabel(job.source_type)}`
            : "Personalized recommendation"}
        </span>
        <div className="job-actions">
          <button
            className="details-button"
            onClick={() =>
              onViewDetails(
                job.job_id
              )
            }
          >
            View Details
          </button>
          <button
            className={
              isSaved
                ? "save-button saved"
                : "save-button"
            }
            onClick={() =>
              onSave(
                job.job_id,
                isSaved
              )
            }
          >
            {isSaved
              ? "Saved"
              : "Save Job"}
          </button>
        </div>
      </div>
    </article>
  );
}
/* =========================================================
   JOB DETAILS
\========================================================= */
function JobDetails({
  job,
  onClose,
}) {
  if (!job) {
    return null;
  }
  const requiredSkills =
    (job.skills || []).filter(
      (skill) =>
        skill.requirement_type ===
        "required"
    );
  const preferredSkills =
    (job.skills || []).filter(
      (skill) =>
        skill.requirement_type ===
        "preferred"
    );
  return (
    <section className="details-panel">
      <div className="details-header">
        <div>
          <p className="eyebrow">
            JOB DETAILS
          </p>
          <div className="details-title-row">
            <h2>
              {cleanText(job.title)}
            </h2>
            {job.is_remote && (
              <span className="remote-badge">
                Remote
              </span>
            )}
          </div>
          <p className="details-company">
            {cleanText(
              job.company_name || ""
            )}
          </p>
          <p className="location">
            {cleanText(
              job.location || ""
            )}
          </p>
        </div>
        <button
          className="close-button"
          onClick={onClose}
        >
          Close
        </button>
      </div>
      <div className="details-grid">
        <div>
          <span>
            Experience
          </span>
          <strong>
            {job.experience_min !== null &&
            job.experience_min !== undefined
              ? `${job.experience_min} years`
              : "Not specified"}
          </strong>
        </div>
        <div>
          <span>
            Work mode
          </span>
          <strong>
            {job.is_remote
              ? "Remote"
              : "On-site / Hybrid"}
          </strong>
        </div>
        <div>
          <span>
            Employment
          </span>
          <strong>
            {cleanText(
              job.employment_type ||
              "Not specified"
            )}
          </strong>
        </div>
        <div>
          <span>
            Function
          </span>
          <strong>
            {cleanText(
              job.job_function ||
              "Not specified"
            )}
          </strong>
        </div>
      </div>
      <div className="details-section">
        <h3>
          Job Description
        </h3>
        <p className="description">
          {cleanText(
            job.description ||
            "No description available."
          )}
        </p>
      </div>
      {requiredSkills.length > 0 && (
        <div className="details-section">
          <h3>
            Required Skills
          </h3>
          <div className="skill-list">
            {requiredSkills.map(
              (skill) => (
                <SkillTag
                  key={skill.skill_id}
                  type="required-gap"
                >
                  {skill.skill_name}
                </SkillTag>
              )
            )}
          </div>
        </div>
      )}
      {preferredSkills.length > 0 && (
        <div className="details-section">
          <h3>
            Preferred Skills
          </h3>
          <div className="skill-list">
            {preferredSkills.map(
              (skill) => (
                <SkillTag
                  key={skill.skill_id}
                  type="preferred-gap"
                >
                  {skill.skill_name}
                </SkillTag>
              )
            )}
          </div>
        </div>
      )}
      <div className="details-footer">
        {(job.application_url || job.source_url) ? (
          <a
            className="apply-button"
            href={job.application_url || job.source_url}
            target="_blank"
            rel="noreferrer"
          >
            {job.source_type
              ? `Open on ${getSourceLabel(job.source_type)}`
              : "Open Original Job"}
          </a>
        ) : (
          <span className="muted">
            Original job link unavailable
          </span>
        )}
      </div>
    </section>
  );
}
/* =========================================================
   PAGINATION
\========================================================= */
function buildPageNumbers(currentPage, totalPages) {
  if (totalPages <= 7) {
    return Array.from(
      { length: totalPages },
      (_, index) => index + 1
    );
  }
  const pages = new Set([1, totalPages]);
  for (
    let page = currentPage - 2;
    page <= currentPage + 2;
    page += 1
  ) {
    if (page >= 1 && page <= totalPages) {
      pages.add(page);
    }
  }
  return [...pages].sort((a, b) => a - b);
}
function RecommendationPagination({
  currentPage,
  totalPages,
  totalItems,
  currentItems,
  loading,
  onPageChange,
}) {
  const pageNumbers = buildPageNumbers(
    currentPage,
    totalPages
  );
  const startItem =
    totalItems === 0
      ? 0
      : (currentPage - 1) * 20 + 1;
  const endItem =
    totalItems === 0
      ? 0
      : Math.min(
          startItem + currentItems - 1,
          totalItems
        );
  return (
    <div className="recommendations-pagination">
      <div className="pagination-summary">
        Showing {startItem}-{endItem} of {totalItems} recommended jobs
      </div>
      <div
        className="pagination-controls"
        aria-label="Recommendation pages"
      >
        <button
          className="pagination-button"
          onClick={() => onPageChange(currentPage - 1)}
          disabled={loading || currentPage === 1}
        >
          Previous
        </button>
        {pageNumbers.map((page, index) => {
          const previousPage = pageNumbers[index - 1];
          const showEllipsis =
            index > 0 && page - previousPage > 1;
          return (
            <Fragment key={page}>
              {showEllipsis && (
                <span className="pagination-ellipsis">
                  ...
                </span>
              )}
              <button
                className={`pagination-button ${
                  page === currentPage ? "active" : ""
                }`}
                onClick={() => onPageChange(page)}
                disabled={loading || page === currentPage}
              >
                {page}
              </button>
            </Fragment>
          );
        })}
        <button
          className="pagination-button"
          onClick={() => onPageChange(currentPage + 1)}
          disabled={loading || currentPage === totalPages}
        >
          Next
        </button>
      </div>
    </div>
  );
}
/* =========================================================
   SAVED JOBS PAGE
\========================================================= */
function SavedJobsPage({
  savedJobs,
  onViewDetails,
  onDelete,
}) {
  return (
    <main className="container saved-page">
      <section className="saved-page-header">
        <div>
          <p className="eyebrow">SAVED JOBS</p>
          <h1>Jobs you saved.</h1>
          <p className="hero-description">
            Keep track of opportunities you want to review later.
          </p>
        </div>
        <div className="saved-page-count">
          <span>Saved</span>
          <strong>{savedJobs.length}</strong>
        </div>
      </section>
      {savedJobs.length > 0 ? (
        <section className="saved-list-page">
          {savedJobs.map((job) => (
            <article
              className="saved-job-card"
              key={job.job_id}
            >
              <div className="saved-job-card-main">
                <div className="saved-job-card-title-row">
                  <h2>{cleanText(job.title)}</h2>
                  {job.source_type && (
                    <span className="saved-source-badge">
                      {getSourceLabel(job.source_type)}
                    </span>
                  )}
                </div>
                <p className="saved-job-company">
                  {cleanText(job.company_name)}
                </p>
                <p className="saved-job-location">
                  {cleanText(
                    job.location ||
                    "Location not specified"
                  )}
                </p>
                <div className="saved-job-meta">
                  <span>
                    {job.is_remote
                      ? "Remote"
                      : "On-site / Hybrid"}
                  </span>
                  <span>
                    {cleanText(
                      job.employment_type ||
                      "Employment not specified"
                    )}
                  </span>
                </div>
              </div>
              <div className="saved-job-actions">
                <button
                  className="details-button"
                  onClick={() =>
                    onViewDetails(job.job_id)
                  }
                >
                  View Details
                </button>
                {(job.application_url ||
                  job.source_url) && (
                  <a
                    className="apply-button"
                    href={
                      job.application_url ||
                      job.source_url
                    }
                    target="_blank"
                    rel="noreferrer"
                  >
                    Open Job
                  </a>
                )}
                <button
                  className="delete-saved-button"
                  onClick={() =>
                    onDelete(job.job_id)
                  }
                  title="Remove from saved jobs"
                >
                  Delete
                </button>
              </div>
            </article>
          ))}
        </section>
      ) : (
        <section className="empty-box saved-empty-page">
          <h3>No saved jobs</h3>
          <p>
            Save a job from your recommendations and it will appear here.
          </p>
        </section>
      )}
    </main>
  );
}
/* =========================================================
   DASHBOARD
\========================================================= */
function Dashboard({
  profileId,
  profileSkills,
  recommendations,
  savedJobIds,
  savedJobs,
  onViewDetails,
  onSave,
  onRefresh,
  onChangeProfile,
  loading,
  recommendationTotal,
  recommendationPage,
  recommendationPageCount,
  paginationLoading,
  onRecommendationPageChange,
  filters,
  onFilterChange,
  onApplyFilters,
  onClearFilters,
  liveSearching,
liveSearchElapsed,
liveSearchResult,
onFindFreshJobs,
}) {
  const allMatchedSkills =
    useMemo(() => {
      const skills = [];
      for (
        const job of recommendations
      ) {
        for (
          const skill of
          job.matched_skills || []
        ) {
          skills.push(
            skill.skill_name
          );
        }
      }
      return [
        ...new Set(skills),
      ];
    }, [recommendations]);
  return (
    <main className="container">
      <section className="dashboard-header">
        <div>
          <h1>
            Recommended jobs for you.
          </h1>
          <p className="hero-description">
            Find opportunities using your resume,
            skills, preferences and job requirements.
          </p>
        </div>
        <div className="dashboard-actions">
          <button
            className="secondary-neu-button"
            onClick={onRefresh}
            disabled={loading}
          >
            {loading
              ? "Refreshing..."
              : "Refresh Jobs"}
          </button>
          <button
  className="live-search-button secondary-neu-button"
  onClick={onFindFreshJobs}
  disabled={liveSearching || loading}
>
  <span className="live-search-content">
    <span className="live-search-dot" />
    {liveSearching
      ? `Searching the web... ${liveSearchElapsed}s`
      : "Find Fresh Jobs"}
  </span>
</button>
          <button
  type="button"
  className="secondary-neu-button"
  onClick={(event) => {
    event.preventDefault();
    event.stopPropagation();
    onChangeProfile();
  }}
>
  Update Resume
</button>
        </div>
      </section>
      {liveSearchResult && (
        <section
          className={`live-search-status ${
            liveSearchResult.status === "success"
              ? "success"
              : "warning"
          }`}
        >
          <p className="live-search-status-title">
            {liveSearchResult.message}
          </p>
          <div className="live-search-status-meta">
            <span>
              Sources: {" "}
              <strong>
                {liveSearchResult.source_count || 0}
              </strong>
            </span>
            <span>
              Fresh jobs: {" "}
              <strong>
                {liveSearchResult.job_count || 0}
              </strong>
            </span>
            <span>
              New: {" "}
              <strong>
                {liveSearchResult.inserted || 0}
              </strong>
            </span>
            <span>
              Updated: {" "}
              <strong>
                {liveSearchResult.updated_existing || 0}
              </strong>
            </span>
            <span>
              Skills extracted: {" "}
              <strong>
                {liveSearchResult.skill_extraction?.total_job_skill_mappings || 0}
              </strong>
            </span>
            <span>
              Jobs with skills: {" "}
              <strong>
                {liveSearchResult.skill_extraction?.jobs_with_detected_skills || 0}
              </strong>
            </span>
            <span>
              Without skills: {" "}
              <strong>
                {liveSearchResult.skill_extraction?.jobs_without_detected_skills || 0}
              </strong>
            </span>
          </div>
        </section>
      )}
      <section className="summary-card">
        <div>
          <span>
            Recommended jobs
          </span>
          <strong>
            {recommendationTotal}
          </strong>
        </div>
        <div>
          <span>
            Saved jobs
          </span>
          <strong>
            {savedJobs.length}
          </strong>
        </div>
        <div>
          <span>
            Profile
          </span>
          <strong>
            Ready
          </strong>
        </div>
      </section>
      <FilterPanel
        filters={filters}
        onChange={onFilterChange}
        onApply={onApplyFilters}
        onClear={onClearFilters}
        loading={loading}
      />
      <section className="skills-summary">
        <div className="section-heading">
          <div>
            <p className="eyebrow">
              RESUME SKILLS
            </p>
            <h2>
              Skills detected from your resume
            </h2>
          </div>
        </div>
        {profileSkills.length > 0 ? (
          <div className="skill-list large">
            {profileSkills.map(
              (skill) => (
                <SkillTag
                  key={
                    skill.skill_id ||
                    skill.skill_name
                  }
                  type="profile"
                >
                  {skill.skill_name}
                </SkillTag>
              )
            )}
          </div>
        ) : allMatchedSkills.length > 0 ? (
          <div className="skill-list large">
            {allMatchedSkills.map(
              (skill) => (
                <SkillTag
                  key={skill}
                  type="profile"
                >
                  {skill}
                </SkillTag>
              )
            )}
          </div>
        ) : (
          <p className="muted">
            No skills available yet.
          </p>
        )}
      </section>
      <section className="recommendations-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">
              RECOMMENDATIONS
            </p>
            <h2>
              Jobs for you ({recommendationTotal})
            </h2>
            <p className="section-caption">
              Live jobs are shown first, with the newest postings first.
            </p>
          </div>
        </div>
        {loading ? (
          <div className="loading-box">
            <div className="loader" />
            <p>
              Finding suitable jobs...
            </p>
          </div>
        ) : recommendations.length > 0 ? (
          <>
          <div className="job-list">
            {recommendations.map(
              (job) => (
                <JobCard
                  key={job.job_id}
                  job={job}
                  isSaved={
                    savedJobIds.includes(
                      job.job_id
                    )
                  }
                  onViewDetails={
                    onViewDetails
                  }
                  onSave={
                    onSave
                  }
                />
              )
            )}
          </div>
          {recommendationTotal > 0 && (
            <RecommendationPagination
              currentPage={recommendationPage}
              totalPages={recommendationPageCount}
              totalItems={recommendationTotal}
              currentItems={recommendations.length}
              loading={paginationLoading}
              onPageChange={onRecommendationPageChange}
            />
          )}
          </>
        ) : (
          <div className="empty-box">
            <h3>
              No jobs match your filters
            </h3>
            <p>
              Try a broader location, lower
              minimum match score, or clear
              some filters.
            </p>
          </div>
        )}
      </section>
    </main>
  );
}
/* =========================================================
   MAIN APP
\========================================================= */
function App() {
  const [profileId, setProfileId] =
    useState(
      localStorage.getItem(
        PROFILE_STORAGE_KEY
      )
    );
    const [liveSearching, setLiveSearching] =
  useState(false);
const [liveSearchResult, setLiveSearchResult] =
  useState(null);
  const [liveSearchElapsed, setLiveSearchElapsed] =
    useState(0);
  const [jobFetchNotice, setJobFetchNotice] =
    useState(false);
  const [currentView, setCurrentView] =
    useState("recommendations");
  async function handleFindFreshJobs() {
    if (!profileId || liveSearching || jobFetchNotice) {
      return;
    }
    setLiveSearching(true);
    setJobFetchNotice(true);
    setLiveSearchElapsed(0);
    setLiveSearchResult(null);
    setError("");
    try {
      const data = await findFreshJobs(
        Number(profileId)
      );
      setLiveSearchResult(data);
      if (data.status === "success") {
        await loadRecommendations(
          profileId,
          filters
        );
        await loadSavedJobs(profileId);
        setCurrentView("recommendations");
      }
    } catch (err) {
      setLiveSearchResult(null);
      setError(
        err.message ||
        "Could not search for fresh jobs."
      );
    } finally {
      setLiveSearching(false);
      setJobFetchNotice(false);
    }
  }
  const [profileSkills, setProfileSkills] =
    useState(() => {
      try {
        return JSON.parse(
          localStorage.getItem(
            SKILLS_STORAGE_KEY
          ) || "[]"
        );
      } catch {
        return [];
      }
    });
  const RECOMMENDATION_PAGE_SIZE = 20;
  const [recommendations, setRecommendations] =
    useState([]);
  const [recommendationPage, setRecommendationPage] =
    useState(1);
  const [recommendationTotal, setRecommendationTotal] =
    useState(0);
  const [recommendationHasMore, setRecommendationHasMore] =
    useState(false);
  const [paginationLoading, setPaginationLoading] =
    useState(false);
  const [savedJobIds, setSavedJobIds] =
    useState([]);
  const [savedJobs, setSavedJobs] =
    useState([]);
  const [selectedJob, setSelectedJob] =
    useState(null);
  const [filters, setFilters] =
    useState(
      DEFAULT_FILTERS
    );
  const [loading, setLoading] =
    useState(false);
  const [detailsLoading, setDetailsLoading] =
    useState(false);
  const [error, setError] =
    useState("");
  const [backendOnline, setBackendOnline] =
    useState(false);
  const [showOnboarding, setShowOnboarding] =
  useState(!profileId);

const [showProfileEditor, setShowProfileEditor] =
  useState(false);
  async function loadRecommendations(
    currentProfileId = profileId,
    currentFilters = filters
  ) {
    if (!currentProfileId) {
      return;
    }
    setLoading(true);
    setError("");
    setRecommendationPage(1);
    setRecommendationTotal(0);
    setRecommendationHasMore(false);
    try {
      const data = await getRecommendations(
        Number(currentProfileId),
        RECOMMENDATION_PAGE_SIZE,
        currentFilters,
        1,
        RECOMMENDATION_PAGE_SIZE
      );
      const jobs = data.recommendations || [];
      setRecommendations(jobs);
      setRecommendationPage(Number(data.page || 1));
      setRecommendationTotal(Number(data.count || 0));
      setRecommendationHasMore(
        Boolean(data.has_more)
      );
    } catch (err) {
      setRecommendations([]);
      setRecommendationPage(1);
      setRecommendationTotal(0);
      setRecommendationHasMore(false);
      setError(
        err.message ||
        "Could not load recommendations."
      );
    } finally {
      setLoading(false);
    }
  }
  async function handleRecommendationPageChange(page) {
    const safePage = Math.min(
      Math.max(1, Number(page) || 1),
      recommendationPageCount
    );
    if (
      !profileId ||
      safePage === recommendationPage ||
      paginationLoading
    ) {
      return;
    }
    setPaginationLoading(true);
    setError("");
    try {
      const data = await getRecommendations(
        Number(profileId),
        RECOMMENDATION_PAGE_SIZE,
        filters,
        safePage,
        RECOMMENDATION_PAGE_SIZE
      );
      const jobs = data.recommendations || [];
      const total = Number(
        data.count || recommendationTotal
      );
      setRecommendations(jobs);
      setRecommendationPage(
        Number(data.page || safePage)
      );
      setRecommendationTotal(total);
      setRecommendationHasMore(
        Boolean(data.has_more)
      );
      window.requestAnimationFrame(() => {
        document
          .querySelector(".recommendations-section")
          ?.scrollIntoView({
            behavior: "smooth",
            block: "start",
          });
      });
    } catch (err) {
      setError(
        err.message ||
        "Could not change recommendation page."
      );
    } finally {
      setPaginationLoading(false);
    }
  }
  async function loadSavedJobs(
    currentProfileId = profileId
  ) {
    if (!currentProfileId) {
      return;
    }
    try {
      const ids =
        await getSavedJobIds(
          Number(currentProfileId)
        );
      setSavedJobIds(
        ids.job_ids || []
      );
      const saved =
        await getSavedJobs(
          Number(currentProfileId)
        );
      setSavedJobs(
        saved.jobs || []
      );
    } catch {
      setSavedJobIds([]);
      setSavedJobs([]);
    }
  }
  async function handleOnboardingCompleted(
    data
  ) {
    const newProfileId =
      String(data.profile_id);
    localStorage.setItem(
      PROFILE_STORAGE_KEY,
      newProfileId
    );
    localStorage.setItem(
      SKILLS_STORAGE_KEY,
      JSON.stringify(
        data.resume?.skills || []
      )
    );
    setProfileId(
      newProfileId
    );
    setProfileSkills(
      data.resume?.skills || []
    );
    setRecommendations([]);
    setRecommendationPage(1);
    setRecommendationTotal(0);
    setRecommendationHasMore(false);
    setFilters({
      ...DEFAULT_FILTERS,
    });
    setSelectedJob(null);
    setShowOnboarding(false);
    setCurrentView("recommendations");
    setError("");
    await loadRecommendations(
      newProfileId,
      DEFAULT_FILTERS
    );
    await loadSavedJobs(
      newProfileId
    );
  }
  async function handleViewDetails(
    jobId
  ) {
    setDetailsLoading(true);
    setError("");
    try {
      const data =
        await getJobDetails(
          jobId
        );
      setSelectedJob(data);
      window.scrollTo({
        top: 0,
        behavior: "smooth",
      });
    } catch (err) {
      setError(
        err.message ||
        "Could not load job details."
      );
    } finally {
      setDetailsLoading(false);
    }
  }
  async function handleSaveJob(
    jobId,
    alreadySaved
  ) {
    if (!profileId) {
      return;
    }
    try {
      if (alreadySaved) {
        await removeSavedJob(
          Number(profileId),
          jobId
        );
        setSavedJobIds(
          (current) =>
            current.filter(
              (id) => id !== jobId
            )
        );
      } else {
        await saveJob(
          Number(profileId),
          jobId
        );
        setSavedJobIds(
          (current) => [
            ...current,
            jobId,
          ]
        );
      }
      await loadSavedJobs();
    } catch (err) {
      setError(
        err.message ||
        "Could not update saved job."
      );
    }
  }
  async function handleRefresh() {
    if (jobFetchNotice || loading || liveSearching) {
      return;
    }
    setCurrentView("recommendations");
    setJobFetchNotice(true);
    setError("");
    try {
      await loadRecommendations(
        profileId,
        filters
      );
      await loadSavedJobs();
    } catch (err) {
      setError(
        err.message ||
        "Could not refresh jobs."
      );
    } finally {
      setJobFetchNotice(false);
    }
  }
  async function handleApplyFilters() {
    await loadRecommendations(
      profileId,
      filters
    );
  }
  async function handleClearFilters() {
    const clearedFilters = {
      ...DEFAULT_FILTERS,
    };
    setFilters(
      clearedFilters
    );
    await loadRecommendations(
      profileId,
      clearedFilters
    );
  }
  function handleChangeProfile() {
  setShowProfileEditor(true);
  setSelectedJob(null);
  setError("");

  window.scrollTo({
    top: 0,
    behavior: "smooth",
  });
}

function handleCancelProfileUpdate() {
  setShowProfileEditor(false);
  setError("");

  window.scrollTo({
    top: 0,
    behavior: "smooth",
  });
}
  useEffect(() => {
    if (!liveSearching) {
      return undefined;
    }
    const timer = window.setInterval(() => {
      setLiveSearchElapsed((current) => current + 1);
    }, 1000);
    return () => window.clearInterval(timer);
  }, [liveSearching]);
  useEffect(() => {
    if (!liveSearchResult) {
      return undefined;
    }
    const timer = window.setTimeout(() => {
      setLiveSearchResult(null);
    }, 3000);
    return () => window.clearTimeout(timer);
  }, [liveSearchResult]);
  useEffect(() => {
    async function checkBackend() {
      try {
        await getHealth();
        setBackendOnline(true);
      } catch {
        setBackendOnline(false);
      }
    }
    checkBackend();
  }, []);
useEffect(() => {
  if (
    !profileId ||
    showOnboarding ||
    showProfileEditor
  ) {
    return;
  }

  loadRecommendations(
    profileId,
    DEFAULT_FILTERS
  );

  loadSavedJobs(
    profileId
  );
}, [
  profileId,
  showOnboarding,
  showProfileEditor,
]);
  const recommendationPageCount = Math.max(
    1,
    Math.ceil(
      recommendationTotal / RECOMMENDATION_PAGE_SIZE
    )
  );
  function handleViewChange(view) {
    setCurrentView(view);
    setSelectedJob(null);
    setError("");
    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });
  }
  if (showOnboarding || showProfileEditor) {
    return (
      <div className="app">
        <header className="topbar">
          <div>
            <div className="brand">
              ORBIT-JR
            </div>
            <div className="brand-subtitle">
              Job discovery for students
            </div>
          </div>
          <div
            className={
              backendOnline
                ? "backend-status online"
                : "backend-status offline"
            }
          >
            <span className="status-dot" />
            {backendOnline
              ? "Backend online"
              : "Backend offline"}
          </div>
        </header>
        <OnboardingForm
  onCompleted={(data) => {
    setShowProfileEditor(false);
    handleOnboardingCompleted(data);
  }}
/>
      </div>
    );
  }
  return (
    <div className="app">
      <header className="topbar">
        <div className="topbar-brand-block">
          <div className="brand">
            ORBIT-JR
          </div>
          <div className="brand-subtitle">
            Job discovery for students
          </div>
        </div>
        <nav className="topbar-nav" aria-label="Main navigation">
          <button
            className={`nav-button ${
              currentView === "recommendations" ? "active" : ""
            }`}
            onClick={() =>
              handleViewChange("recommendations")
            }
          >
            Recommended Jobs
          </button>
          <button
            className={`nav-button ${
              currentView === "saved" ? "active" : ""
            }`}
            onClick={() =>
              handleViewChange("saved")
            }
          >
            Saved Jobs
            <span className="nav-count">
              {savedJobs.length}
            </span>
          </button>
        </nav>
        <div
          className={
            backendOnline
              ? "backend-status online"
              : "backend-status offline"
          }
        >
          <span className="status-dot" />
          {backendOnline
            ? "Backend online"
            : "Backend offline"}
        </div>
      </header>
      {jobFetchNotice && (
        <div
          className="job-fetch-toast"
          role="status"
          aria-live="polite"
        >
          <div className="job-fetch-toast-loader">
            <span className="mini-loader" />
          </div>
          <div>
            <strong>Jobs are being fetched</strong>
            <p>
              It may take around 2 minute. Please wait...
            </p>
          </div>
        </div>
      )}
      {error && (
        <div className="global-error">
          <div>
            <strong>
              Something went wrong
            </strong>
            <p>
              {error}
            </p>
          </div>
          <button
            onClick={() =>
              setError("")
            }
          >
            Close
          </button>
        </div>
      )}
      {selectedJob && (
        <main className="container">
          <JobDetails
            job={selectedJob}
            onClose={() =>
              setSelectedJob(null)
            }
          />
          {detailsLoading && (
            <div className="details-loading">
              Loading job details...
            </div>
          )}
        </main>
      )}
      {currentView === "saved" ? (
        <SavedJobsPage
          savedJobs={savedJobs}
          onViewDetails={handleViewDetails}
          onDelete={(jobId) =>
            handleSaveJob(jobId, true)
          }
        />
      ) : (
        <Dashboard
          liveSearching={liveSearching}
          liveSearchElapsed={liveSearchElapsed}
          liveSearchResult={liveSearchResult}
          onFindFreshJobs={handleFindFreshJobs}
          profileId={profileId}
          profileSkills={profileSkills}
          recommendations={recommendations}
          savedJobIds={savedJobIds}
          savedJobs={savedJobs}
          onViewDetails={handleViewDetails}
          onSave={handleSaveJob}
          onRefresh={handleRefresh}
          onChangeProfile={handleChangeProfile}
          loading={loading}
          recommendationTotal={recommendationTotal}
          recommendationPage={recommendationPage}
          recommendationPageCount={recommendationPageCount}
          paginationLoading={paginationLoading}
          onRecommendationPageChange={
            handleRecommendationPageChange
          }
          filters={filters}
          onFilterChange={setFilters}
          onApplyFilters={handleApplyFilters}
          onClearFilters={handleClearFilters}
        />
      )}
    </div>
  );
}
export default App;
