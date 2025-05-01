import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer } from 'recharts';

const Matches = () => {
  const [jobs, setJobs] = useState([]);
  const [expandedJobId, setExpandedJobId] = useState(null);
  const [matchedApplicants, setMatchedApplicants] = useState({});
  const [applicantInfo, setApplicantInfo] = useState({}); // applicantId -> parsed_json
  const [selectedJob, setSelectedJob] = useState(null);
  const [selectedApplicantId, setSelectedApplicantId] = useState(null);
  const [matchDetails, setMatchDetails] = useState(null);
  const [activeTab, setActiveTab] = useState('');
  const [debateOpen, setDebateOpen] = useState(false);
  const [debateData, setDebateData] = useState(null);

  useEffect(() => {
    axios.get("http://localhost:8000/status")
      .then(res => {
        setJobs(res.data.filter(f => f.file_type === "job_posting"));
      })
      .catch(err => console.error("Failed to fetch job postings", err));
  }, []);

  const handleSelectJob = async (job) => {
    if (expandedJobId === job.id) {
      setExpandedJobId(null);
      setSelectedJob(null);
      setSelectedApplicantId(null);
      setMatchDetails(null);
      setActiveTab('');
      return;
    }

    setExpandedJobId(job.id);
    setSelectedJob(job);
    setSelectedApplicantId(null);
    setMatchDetails(null);
    setActiveTab('');

    try {
      const response = await axios.get(`http://localhost:8000/matches/${job.id}`);
      const applicantIds = response.data;
      setMatchedApplicants(prev => ({ ...prev, [job.id]: applicantIds }));

      // Fetch applicant names
      const info = {};
      for (const applicantId of applicantIds) {
        const detailRes = await axios.get(`http://localhost:8000/details?id=${applicantId}`);
        info[applicantId] = detailRes.data;
      }
      setApplicantInfo(prev => ({ ...prev, ...info }));

    } catch (err) {
      console.error("Failed to fetch matches or applicant info", err);
    }
  };

  const handleSelectApplicant = async (applicantId) => {
    setSelectedApplicantId(applicantId);
    setActiveTab('Summary');

    try {
      const response = await axios.get(`http://localhost:8000/match_details?applicant_id=${applicantId}&job_id=${selectedJob.id}`);
      if (!response.data.error) {
        setMatchDetails(response.data);
      } else {
        setMatchDetails(null);
      }
    } catch (err) {
      console.error("Failed to fetch match details", err);
      setMatchDetails(null);
    }
  };

  const formatName = (name) => {
    if (!name) return '';
    return name.toLowerCase().split(' ').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
  };

  const getApplicantDisplayName = (applicantId) => {
    const info = applicantInfo[applicantId];
    if (info && info.name) {
      return formatName(info.name);
    }
    return `Applicant`; // fallback if no name found
  };

  const renderAgentTabs = () => {
    if (!matchDetails) return <p>Select an applicant to view evaluation.</p>;

    const parsedRecruiter = parseEvaluation(matchDetails.recruiter_agent);
    const parsedHiringManager = parseEvaluation(matchDetails.hiring_manager_agent);

    const getFinalRecommendation = (rawText) => {
      if (!rawText) return 'Unknown';
      const lowered = rawText.toLowerCase();
      if (lowered.includes('final recommendation: **yes**') || lowered.includes('final recommendation: yes')) {
        return 'Yes';
      }
      if (lowered.includes('final recommendation: **no**') || lowered.includes('final recommendation: no')) {
        return 'No';
      }
      return 'Unknown';
    };

    const recruiterDecision = getFinalRecommendation(matchDetails.recruiter_agent);
    const managerDecision = getFinalRecommendation(matchDetails.hiring_manager_agent);

    const getBannerStyle = (decision) => {
      if (decision === 'Yes') return styles.greenBanner;
      if (decision === 'No') return styles.redBanner;
      return styles.grayBanner;
    };

    const handleViewDebate = () => {
      setDebateData(matchDetails.debate_transcript);
      setDebateOpen(true);
    };    
    
    const extractOverallScore = (text) => {
        if (!text) return 5; // Neutral if no text
        
        const lines = text.split(/\n+/).filter(Boolean);
        
        for (const line of lines) {
          if (line.toLowerCase().includes('overall')) {
            const match = line.match(/(\d+)\/10/i);
            if (match) {
              return parseInt(match[1]);
            }
          }
        }
        
        return 5; // Default if no score found
      };
      
    const buildRadarData = () => {
        const data = [];
      
        if (matchDetails.recruiter_agent) {
          const score = extractOverallScore(matchDetails.recruiter_agent);
          data.push({ agent: 'Recruiter Agent', score });
        }
        
        if (matchDetails.hiring_manager_agent) {
          const score = extractOverallScore(matchDetails.hiring_manager_agent);
          data.push({ agent: 'Hiring Manager Agent', score });
        }
      
        // ✨ Later you can add more agents like:
        // if (matchDetails.engineering_lead_agent) { ... }
        // if (matchDetails.hr_agent) { ... }
      
        return data;
      };     
    
      const renderDebateButton = () => {
        if (!matchDetails) return null;
      
        const hasDebate =
          matchDetails &&
          matchDetails.debate_transcript &&
          matchDetails.debate_transcript.length > 0;

      
        return (
          <div style={{ textAlign: 'center', marginTop: '15px', marginBottom: '25px' }}>
            <button
              style={hasDebate ? styles.debateButton : styles.disabledDebateButton}
              disabled={!hasDebate}
              onClick={hasDebate ? handleViewDebate : undefined}
            >
              {hasDebate ? "View Debate" : "No Debate: Agents Agreed"}
            </button>
          </div>
        );
      }; 
      
    /* ---------- popup modal ------------------------------------ */
    const renderDebateModal = () =>
      debateOpen && debateData && (
        <div style={styles.overlay}>
          <div style={styles.modal}>
            {/* close button */}
            <button style={styles.closeBtn} onClick={() => setDebateOpen(false)}>
              ×
            </button>

            {/* winner banner */}
            {matchDetails.debate_winner && (
              <div style={{ ...styles.bannerBase, ...styles.greenBanner, marginBottom: 12 }}>
                Debate Winner:&nbsp;
                {matchDetails.debate_winner.toLowerCase().includes("recruiter")
                  ? "Recruiter Agent"
                  : "Hiring Manager Agent"}
              </div>
            )}

            <h3 style={styles.modalTitle}>Debate Transcript</h3>

            <div style={styles.chatArea}>
              {debateData.slice(2).map((entry, idx) => {
                const isRecruiter = entry.source.toLowerCase().includes("recruiter");
                const cleanText = entry.text.replace(/"/g, "");   // strip quotes
                return (
                  <div
                    key={idx}
                    style={{
                      ...styles.bubbleBase,
                      ...(isRecruiter ? styles.leftBubble : styles.rightBubble),
                    }}
                  >
                    <strong>{entry.source.replace("Agent", "")}: </strong>
                    {cleanText}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      );

    return (
      <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
        <div style={styles.tabsContainer}>
            <div
                style={{ ...styles.tab, ...(activeTab === 'Summary' ? styles.activeTab : {}) }}
                onClick={() => setActiveTab('Summary')}
            >
                Summary
            </div>
            <div
                style={{ ...styles.tab, ...(activeTab === 'Recruiter Agent' ? styles.activeTab : {}) }}
                onClick={() => setActiveTab('Recruiter Agent')}
            >
                Recruiter Agent
            </div>
            <div
                style={{ ...styles.tab, ...(activeTab === 'Hiring Manager Agent' ? styles.activeTab : {}) }}
                onClick={() => setActiveTab('Hiring Manager Agent')}
            >
                Hiring Manager Agent
            </div>
        </div>

        <div style={styles.tabContent}>

        {activeTab === 'Summary' && (
        <div style={{ height: '400px', width: '100%', marginTop: '20px' }}>
            <ResponsiveContainer width="100%" height="100%">
            <RadarChart outerRadius={150} data={buildRadarData()}>
                <PolarGrid />
                <PolarAngleAxis dataKey="agent" />
                <PolarRadiusAxis angle={30} domain={[0, 10]} />
                <Radar name="Evaluation" dataKey="score" stroke="#8884d8" fill="#8884d8" fillOpacity={0.6} />
            </RadarChart>
            </ResponsiveContainer>
        </div>
        )}

          {activeTab === 'Recruiter Agent' && (
            <>
              <div style={{ ...styles.bannerBase, ...getBannerStyle(recruiterDecision) }}>
                Final Recommendation: {recruiterDecision}
              </div>
              <div style={styles.agentEvaluationBox}>
                {parsedRecruiter.map((section, idx) => (
                  <div key={idx} style={styles.sectionCard}>
                    <h4 style={styles.sectionTitle}>{section.title}</h4>
                    <p style={styles.sectionContent}>{section.content}</p>
                  </div>
                ))}
              </div>
            </>
          )}

            {activeTab === 'Hiring Manager Agent' && (
            <>
                <div style={{ ...styles.bannerBase, ...getBannerStyle(managerDecision) }}>
                Final Recommendation: {managerDecision}
                </div>
                {renderDebateButton()}
                <div style={styles.agentEvaluationBox}>
                {parsedHiringManager.map((section, idx) => (
                    <div key={idx} style={styles.sectionCard}>
                    <h4 style={styles.sectionTitle}>{section.title}</h4>
                    <p style={styles.sectionContent}>{section.content}</p>
                    </div>
                ))}
                </div>
            </>
            )}
            {renderDebateModal()}
        </div>
      </div>
    );
  };

  const parseEvaluation = (text) => {
    if (!text) return [];

    const lines = text.split(/\n+/).filter(Boolean);
    const sections = [];
    let currentTitle = '';
    let currentContent = '';

    lines.forEach((line) => {
      const match = line.match(/^\s*(\d+)\.\s*\*\*(.+?)\*\*\s*:*/);
      if (match) {
        if (currentTitle) {
          sections.push({ title: currentTitle, content: currentContent.trim() });
        }
        currentTitle = match[2].trim();
        currentContent = line.replace(match[0], '').trim();
      } else {
        currentContent += ' ' + line.trim();
      }
    });

    if (currentTitle) {
      sections.push({ title: currentTitle, content: currentContent.trim() });
    }

    // Remove Final Recommendation duplication
    if (sections.length > 0) {
      const last = sections[sections.length - 1];
      if (last.content) {
        last.content = last.content.replace(/Final recommendation:.*/i, '').trim();
      }
    }

    return sections;
  };

  return (
    <div style={{ display: 'flex', padding: '20px', height: 'calc(100vh - 80px)' }}>
      {/* Left side: Jobs + Applicants */}
      <div style={{ width: '30%', overflowY: 'auto', marginRight: '20px' }}>
        <h2>Job Postings</h2>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <tbody>
            {jobs.map((job, index) => (
              <React.Fragment key={job.id}>
                <tr
                  style={{
                    backgroundColor: selectedJob?.id === job.id ? '#ede7f6' : (index % 2 === 0 ? '#fff' : '#f0f0f0'),
                    cursor: 'pointer',
                    transition: 'background-color 0.3s ease'
                  }}
                  onClick={() => handleSelectJob(job)}
                >
                  <td style={styles.td}>{job.original_name || job.file_name}</td>
                </tr>

                {expandedJobId === job.id && matchedApplicants[job.id]?.length > 0 && (
                  matchedApplicants[job.id].map((applicantId) => (
                    <tr
                      key={applicantId}
                      style={{
                        backgroundColor: selectedApplicantId === applicantId ? '#d1c4e9' : '#f7f7f7',
                        cursor: 'pointer',
                        transition: 'background-color 0.3s ease'
                      }}
                      onClick={() => handleSelectApplicant(applicantId)}
                    >
                      <td style={styles.matchedTd}>
                        ↳ {getApplicantDisplayName(applicantId)}
                      </td>
                    </tr>
                  ))
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>

      {/* Right side: Agent Tabs */}
      <div style={{ width: '70%', background: 'rgba(255,255,255,0.8)', borderRadius: '16px', backdropFilter: 'blur(12px)', padding: '25px', boxShadow: '0 4px 12px rgba(0,0,0,0.1)', overflowY: 'auto' }}>
        {renderAgentTabs()}
      </div>
    </div>
  );
};


const styles = {
  td: {
    padding: '12px',
    borderBottom: '1px solid #ddd',
    fontWeight: 'bold',
    color: '#003366'
  },
  matchedTd: {
    padding: '10px 30px',
    fontSize: '14px',
    color: '#555',
    backgroundColor: '#f7f7f7'
  },
  tabsContainer: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    flexWrap: 'wrap',
    overflow: 'visible',        // ✨ both X and Y should be visible
    paddingBottom: '8px',
    marginBottom: '10px',
    borderBottom: '1px solid #ccc',
    flexShrink: 0,              // ✨ VERY IMPORTANT: prevent the container from shrinking and causing scroll
  },
    tab: {
    padding: '10px 20px 8px 20px',
    backgroundColor: '#e0e0e0',
    borderTopLeftRadius: '10px',
    borderTopRightRadius: '10px',
    border: '1px solid #ccc',
    borderBottom: 'none',
    fontSize: '14px',
    fontWeight: 'bold',
    color: '#555',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
    },
    activeTab: {
    backgroundColor: '#ffffff',
    color: '#a020f0',
    border: '1px solid #a020f0',
    borderBottom: 'none',
    boxShadow: '0 -2px 8px rgba(160, 32, 240, 0.2)',
    },
    summaryBox: {
    padding: '20px',
    backgroundColor: '#f9f9f9',
    borderRadius: '12px',
    marginTop: '20px',
    boxShadow: '0px 4px 10px rgba(0,0,0,0.05)',
    },
tabContent: {
    flexGrow: 1,
    padding: '20px',
    border: '1px solid #ccc',
    borderRadius: '10px',
    backgroundColor: '#fff',
    overflowY: 'auto',   // ✅ scrolling should only happen for the CONTENT, not the tabs!
    height: '100%',      // optional to ensure it fills available space nicely
    },
  pre: {
    fontFamily: 'monospace',
    whiteSpace: 'pre-wrap',
    wordWrap: 'break-word'
  },
  agentEvaluationBox: {
    backgroundColor: 'rgba(255,255,255,0.6)',
    padding: '20px',
    borderRadius: '12px',
    boxShadow: '0px 8px 20px rgba(160,32,240,0.15)',
    backdropFilter: 'blur(10px)',
  },
  sectionCard: {
    marginBottom: '20px',
    padding: '15px',
    backgroundColor: 'white',
    borderRadius: '10px',
    boxShadow: '0px 4px 10px rgba(0,0,0,0.05)',
  },
  sectionTitle: {
    fontSize: '18px',
    color: '#6a1b9a',
    marginBottom: '10px',
    fontWeight: 'bold'
  },
  sectionContent: {
    fontSize: '15px',
    color: '#444',
    lineHeight: '1.5'
  },
  bannerBase: {
    fontWeight: 'bold',
    padding: '10px',
    borderRadius: '8px',
    marginBottom: '20px',
    textAlign: 'center',
    fontSize: '16px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
  },
  greenBanner: {
    backgroundColor: '#e8f5e9',
    color: '#2e7d32',
  },
  redBanner: {
    backgroundColor: '#ffebee',
    color: '#c62828',
  },
  grayBanner: {
    backgroundColor: '#f5f5f5',
    color: '#555',
  },
  debateButton: {
    background: 'linear-gradient(to right, #a020f0, #d17bff)',
    color: 'white',
    fontWeight: 'bold',
    padding: '10px 24px',
    fontSize: '14px',
    border: 'none',
    borderRadius: '20px',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
    boxShadow: '0px 4px 12px rgba(160, 32, 240, 0.3)',
  },
  disabledDebateButton: {
    background: '#e0e0e0',
    color: '#888',
    fontWeight: 'bold',
    padding: '10px 24px',
    fontSize: '14px',
    border: 'none',
    borderRadius: '20px',
    cursor: 'not-allowed',
    opacity: 0.7,
  },
    /* ─── modal overlay ─────────────────────────────────────── */
    overlay: {
      position: "fixed",
      inset: 0,
      background: "rgba(0,0,0,0.55)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      zIndex: 9999,
    },
    modal: {
      position: "relative",
      width: "min(1000px, 90vw)",
      maxHeight: "80vh",
      background: "#ffffff",
      borderRadius: "16px",
      boxShadow: "0 20px 40px rgba(0,0,0,0.25)",
      padding: "32px 24px 24px",
      overflowY: "auto",
      display: "flex",
      flexDirection: "column",
    },
    closeBtn: {
      position: "absolute",
      top: "12px",
      right: "14px",
      fontSize: "26px",
      border: "none",
      background: "transparent",
      cursor: "pointer",
      lineHeight: 1,
    },
    modalTitle: {
      margin: "0 0 16px 0",
      textAlign: "center",
    },
  
    /* ─── chat bubbles ──────────────────────────────────────── */
    chatArea: {
      display: "flex",
      flexDirection: "column",
      gap: "12px",
    },
    bubbleBase: {
      padding: "10px 14px",
      borderRadius: "18px",
      fontSize: "14px",
      lineHeight: 1.4,
      maxWidth: "85%",
      wordBreak: "break-word",
      boxShadow: "0 2px 6px rgba(0,0,0,0.1)",
    },
    leftBubble: {
      alignSelf: "flex-start",
      background: "#e3f2fd",           /* light blue */
      color: "#0d47a1",
    },
    rightBubble: {
      alignSelf: "flex-end",
      background: "#f3e5f5",           /* light purple */
      color: "#4a148c",
    },
  };
export default Matches;
