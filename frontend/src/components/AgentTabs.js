// src/components/AgentTabs.js
import React from 'react';
import {
  ResponsiveContainer,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis
} from 'recharts';

const AgentTabs = ({
  matchDetails,
  activeTab,
  setActiveTab,
  parsedRecruiter,
  parsedHiringManager,
  parseEvaluation,
  styles,
  handleViewDebate,
  debateData,
  debateOpen,
  setDebateOpen
}) => {
  const getFinalRecommendation = (text) => {
    if (!text) return 'Unknown';
    const lowered = text.toLowerCase();
    if (lowered.includes('final recommendation: yes')) return 'Yes';
    if (lowered.includes('final recommendation: no')) return 'No';
    return 'Unknown';
  };

  const recruiterDecision = getFinalRecommendation(matchDetails?.recruiter_agent);
  const managerDecision = getFinalRecommendation(matchDetails?.hiring_manager_agent);
  const portfolioDecision = getFinalRecommendation(matchDetails?.portfolio_agent);
  const techLeadDecision = getFinalRecommendation(matchDetails?.technical_lead_agent);

  const getBannerStyle = (decision) => {
    if (decision === 'Yes') return styles.greenBanner;
    if (decision === 'No') return styles.redBanner;
    return styles.grayBanner;
  };

  const extractOverallScore = (text) => {
    if (!text) return 5;
    const match = text.match(/(\d+)\/10/i);
    return match ? parseInt(match[1]) : 5;
  };

  const interpolateColor = (value) => {
    const clamp = (v) => Math.max(0, Math.min(v, 10));
  
    const r1 = [231, 76, 60];     // red
    const r2 = [241, 196, 15];    // yellow
    const r3 = [46, 204, 113];    // green
  
    const v = clamp(value);
  
    let from, to, t;
  
    if (v <= 5) {
      from = r1;
      to = r2;
      t = v / 5;
    } else {
      from = r2;
      to = r3;
      t = (v - 5) / 5;
    }
  
    const mix = (a, b, t) => Math.round(a + (b - a) * t);
  
    const [r, g, b] = [
      mix(from[0], to[0], t),
      mix(from[1], to[1], t),
      mix(from[2], to[2], t),
    ];
  
    return `rgb(${r}, ${g}, ${b})`;
  };
  

  const CupGauge = ({ value, max = 10 }) => {
    const clamp = (v) => Math.max(0, Math.min(v, max));
    const percent = clamp(value) / max;
  
    // Dimensions
    const cupHeight = 200;
    const cupWidth = 80;
    const cupX = 100;
    const cupY = 20;
    const strokeWidth = 4;
    const fillHeight = percent * cupHeight;
    const fillColor = interpolateColor(value);

    const strokeColor = "#555";
    const tickCount = 5; // 0, 2, 4, 6, 8, 10
  
    return (
      <svg width="300" height="300" viewBox="0 0 300 300">
        {/* Ticks + Labels */}
        {[...Array(tickCount + 1)].map((_, i) => {
          const tickValue = (max / tickCount) * i;
          const y = cupY + cupHeight - (tickValue / max) * cupHeight;
          return (
            <g key={i}>
              <line x1={cupX - 10} x2={cupX} y1={y} y2={y} stroke="#999" strokeWidth="2" />
              <text x={cupX - 14} y={y + 4} fontSize="12" textAnchor="end" fill="#777">
                {tickValue}
              </text>
            </g>
          );
        })}
  
        {/* Cup outline */}
        <rect
          x={cupX}
          y={cupY}
          width={cupWidth}
          height={cupHeight}
          rx="20"
          ry="20"
          fill="none"
          stroke={strokeColor}
          strokeWidth={strokeWidth}
        />
  
        {/* Fill */}
        <rect
          x={cupX}
          y={cupY + (cupHeight - fillHeight)}
          width={cupWidth}
          height={fillHeight}
          fill={fillColor}
          rx="20"
          ry="20"
        />
  
        {/* Score label */}
        <text
          x={cupX + cupWidth / 2}
          y={cupY + cupHeight + 35}
          textAnchor="middle"
          fontSize="32"
          fontWeight="bold"
          fill="#333"
        >
          {clamp(value)}/10
        </text>
  
        <text
          x={cupX + cupWidth / 2}
          y={cupY + cupHeight + 60}
          textAnchor="middle"
          fontSize="16"
          fill="#777"
        >
          Fit Score
        </text>
      </svg>
    );
  };  
  
  const extractFitScore = (text) => {
    if (!text) return null;
  
    // Match both "Fit Score" and "Technical Skill Score", with optional bold and leading number
    const match = text.match(/(?:\d+\.\s*)?\**(fit score|technical skill score)\**[^:]*:\s*(\d+)\s*\/\s*10/i);
    return match ? parseInt(match[2]) : null;
  }; 

  const buildRadarData = () => {
    const data = [];
    if (matchDetails.recruiter_agent) {
      data.push({ agent: 'Recruiter Agent', score: extractOverallScore(matchDetails.recruiter_agent) });
    }
    if (matchDetails.hiring_manager_agent) {
      data.push({ agent: 'Hiring Manager Agent', score: extractOverallScore(matchDetails.hiring_manager_agent) });
    }
    if (matchDetails.portfolio_agent) {
      data.push({ agent: 'Portfolio Agent', score: extractOverallScore(matchDetails.portfolio_agent) });
    }
    if (matchDetails.technical_lead_agent) {
      data.push({ agent: 'Technical Lead Agent', score: extractOverallScore(matchDetails.technical_lead_agent) });
    }
    return data;
  };

  const renderDebateModal = () =>
    debateOpen && debateData && (
      <div style={styles.overlay}>
        <div style={styles.modal}>
          <button style={styles.closeBtn} onClick={() => setDebateOpen(false)}>×</button>
          {matchDetails?.debate_winner && (
            <div style={{ ...styles.bannerBase, ...styles.greenBanner, marginBottom: 12 }}>
              Debate Winner: {matchDetails.debate_winner.toLowerCase().includes("recruiter") ? "Recruiter Agent" : "Hiring Manager Agent"}
            </div>
          )}
          <h3 style={styles.modalTitle}>Debate Transcript</h3>
          <div style={styles.chatArea}>
            {debateData.slice(2).map((entry, idx) => {
              const isRecruiter = entry.source.toLowerCase().includes("recruiter");
              return (
                <div key={idx} style={{ ...styles.bubbleBase, ...(isRecruiter ? styles.leftBubble : styles.rightBubble) }}>
                  <strong>{entry.source.replace("Agent", "")}: </strong>
                  {entry.text.replace(/"/g, "")}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    );

  if (!matchDetails) return <p>Select an applicant to view evaluation.</p>;

  const parsedPortfolio = parseEvaluation(matchDetails.portfolio_agent);
  const parsedTechLead = parseEvaluation(matchDetails.technical_lead_agent);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={styles.tabsContainer}>
        {['Summary', 'Recruiter Agent', 'Hiring Manager Agent', 'Portfolio Agent', 'Technical Lead Agent'].map(tab => (
          <div
            key={tab}
            style={{ ...styles.tab, ...(activeTab === tab ? styles.activeTab : {}) }}
            onClick={() => setActiveTab(tab)}
          >
            {tab}
          </div>
        ))}
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
            <div style={styles.bentoBox}>
            <div style={styles.bentoLeft}>
                {parsedRecruiter
                .filter(section => !/fit score/i.test(section.title))
                .map((section, idx) => (
                    <div key={idx} style={styles.sectionCard}>
                    <h4 style={styles.sectionTitle}>{section.title}</h4>
                    <p style={styles.sectionContent}>{section.content}</p>
                    </div>
                ))}
            </div>

            <div style={styles.bentoRight}>
                <CupGauge value={extractFitScore(matchDetails.recruiter_agent) || 0} />
            </div>
            </div>
        </>
        )}

        {activeTab === 'Hiring Manager Agent' && (
        <>
            <div style={{ ...styles.bannerBase, ...getBannerStyle(managerDecision) }}>
            Final Recommendation: {managerDecision}
            </div>
            <div style={styles.bentoBox}>
            <div style={styles.bentoLeft}>
                {parsedHiringManager
                .filter(section => !/fit score/i.test(section.title))
                .map((section, idx) => (
                    <div key={idx} style={styles.sectionCard}>
                    <h4 style={styles.sectionTitle}>{section.title}</h4>
                    <p style={styles.sectionContent}>{section.content}</p>
                    </div>
                ))}
            </div>

            <div style={styles.bentoRight}>
                <CupGauge value={extractFitScore(matchDetails.hiring_manager_agent) || 0} />
            </div>
            </div>
        </>
        )}


        {activeTab === 'Portfolio Agent' && (
        <>
            {matchDetails.portfolio_agent == null ? (
            <div style={styles.agentEvaluationBox}>
                <p style={{ fontStyle: 'italic', color: '#999' }}>Nothing to see here :(</p>
            </div>
            ) : matchDetails.portfolio_agent.toLowerCase().includes("github fetch error") ||
            matchDetails.portfolio_agent.toLowerCase().includes("no usable github") ? (
            <div style={styles.agentEvaluationBox}>
                <p style={{ fontStyle: 'italic', color: '#999' }}>No usable GitHub link provided :(</p>
            </div>
            ) : (
            <>
                <div style={{ ...styles.bannerBase, ...getBannerStyle(portfolioDecision) }}>
                Final Recommendation: {portfolioDecision}
                </div>
                <div style={styles.bentoBox}>
                <div style={styles.bentoLeft}>
                    {parsedPortfolio
                    .filter(section => !/technical skill score/i.test(section.title))
                    .map((section, idx) => (
                        <div key={idx} style={styles.sectionCard}>
                        <h4 style={styles.sectionTitle}>{section.title}</h4>
                        <p style={styles.sectionContent}>{section.content}</p>
                        </div>
                    ))}
                </div>

                <div style={styles.bentoRight}>
                    <CupGauge value={extractFitScore(matchDetails.portfolio_agent) || 0} />
                </div>
                </div>
            </>
            )}
        </>
        )}


        {activeTab === 'Technical Lead Agent' && (
        <>
            {matchDetails.technical_lead_agent == null ? (
            <div style={styles.agentEvaluationBox}>
                <p style={{ fontStyle: 'italic', color: '#999' }}>Nothing to see here :(</p>
            </div>
            ) : (
            <>
                <div style={{ ...styles.bannerBase, ...getBannerStyle(techLeadDecision) }}>
                Final Recommendation: {techLeadDecision}
                </div>
                <div style={styles.bentoBox}>
                <div style={styles.bentoLeft}>
                    {parsedTechLead
                    .filter(section => !/fit score/i.test(section.title))
                    .map((section, idx) => (
                        <div key={idx} style={styles.sectionCard}>
                        <h4 style={styles.sectionTitle}>{section.title}</h4>
                        <p style={styles.sectionContent}>{section.content}</p>
                        </div>
                    ))}
                </div>

                <div style={styles.bentoRight}>
                    <CupGauge value={extractFitScore(matchDetails.technical_lead_agent) || 0} />
                </div>
                </div>
            </>
            )}
        </>
        )}


        {renderDebateModal()}
      </div>
    </div>
  );
};

export default AgentTabs;
