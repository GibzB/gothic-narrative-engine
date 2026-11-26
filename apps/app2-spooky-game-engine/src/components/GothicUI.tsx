/**
 * Gothic UI Components - Dark-mode React components for narrative engine.
 * 
 * Task 4.2: Implement UI Layer - Dark-mode Gothic React UI
 * Validates: Requirements 4.1, 4.2
 */

import React, { useState, useEffect, useCallback } from 'react';

// Types
interface StoryChoice {
  id: string;
  text: string;
  consequenceScene: string;
  requirement?: Record<string, any>;
  effect?: Record<string, any>;
  isVisible: boolean;
  isAvailable: boolean;
  hint?: string;
}

interface StoryScene {
  id: string;
  title: string;
  description: string;
  phase: string;
  mood: string;
  choices: StoryChoice[];
  atmosphere: {
    fog?: number;
    lightning?: boolean;
    sound?: string;
  };
  isEnding: boolean;
  endingType?: string;
}

interface PlayerState {
  currentScene: string;
  inventory: string[];
  stats: {
    sanity: number;
    courage: number;
    knowledge: number;
    suspicion: number;
  };
  flags: Record<string, boolean>;
  choicesMade: string[];
}

/**
 * Stats Panel Component
 */
export const StatsPanel: React.FC<{ stats: PlayerState['stats'] }> = ({ stats }) => {
  return (
    <div className="stats-panel">
      <div className="stat-item">
        <span className="stat-label">Sanity</span>
        <div style={{ flex: 1, marginLeft: '10px' }}>
          <div className="stat-bar">
            <div 
              className="stat-bar-fill" 
              style={{ width: `${stats.sanity}%` }}
            />
          </div>
          <span className="stat-value">{stats.sanity}</span>
        </div>
      </div>
      <div className="stat-item">
        <span className="stat-label">Courage</span>
        <div style={{ flex: 1, marginLeft: '10px' }}>
          <div className="stat-bar">
            <div 
              className="stat-bar-fill" 
              style={{ width: `${stats.courage}%` }}
            />
          </div>
          <span className="stat-value">{stats.courage}</span>
        </div>
      </div>
      <div className="stat-item">
        <span className="stat-label">Knowledge</span>
        <div style={{ flex: 1, marginLeft: '10px' }}>
          <div className="stat-bar">
            <div 
              className="stat-bar-fill" 
              style={{ width: `${stats.knowledge}%` }}
            />
          </div>
          <span className="stat-value">{stats.knowledge}</span>
        </div>
      </div>
      <div className="stat-item">
        <span className="stat-label">Suspicion</span>
        <div style={{ flex: 1, marginLeft: '10px' }}>
          <div className="stat-bar">
            <div 
              className="stat-bar-fill" 
              style={{ width: `${stats.suspicion}%` }}
            />
          </div>
          <span className="stat-value">{stats.suspicion}</span>
        </div>
      </div>
    </div>
  );
};

/**
 * Inventory Panel Component
 */
export const InventoryPanel: React.FC<{ items: string[] }> = ({ items }) => {
  return (
    <div className="inventory-panel">
      <div className="inventory-title">Inventory</div>
      {items.length === 0 ? (
        <div className="inventory-item" style={{ opacity: 0.5 }}>Empty</div>
      ) : (
        items.map((item, index) => (
          <div key={index} className="inventory-item">
            {item.replace(/_/g, ' ')}
          </div>
        ))
      )}
    </div>
  );
};

/**
 * Choice Button Component
 */
export const ChoiceButton: React.FC<{
  choice: StoryChoice;
  onClick: () => void;
  disabled?: boolean;
}> = ({ choice, onClick, disabled }) => {
  return (
    <button
      className="choice-button"
      onClick={onClick}
      disabled={disabled || !choice.isAvailable}
      title={choice.hint}
    >
      {choice.text}
      {!choice.isAvailable && (
        <span style={{ opacity: 0.5, marginLeft: '10px', fontSize: '0.8em' }}>
          (Requirements not met)
        </span>
      )}
    </button>
  );
};

/**
 * Scene Display Component
 */
export const SceneDisplay: React.FC<{
  scene: StoryScene;
  onChoice: (choiceId: string) => void;
}> = ({ scene, onChoice }) => {
  const [displayedText, setDisplayedText] = useState('');
  const [isTyping, setIsTyping] = useState(true);

  // Typewriter effect
  useEffect(() => {
    setDisplayedText('');
    setIsTyping(true);

    let index = 0;
    const text = scene.description;
    const interval = setInterval(() => {
      if (index < text.length) {
        setDisplayedText(text.slice(0, index + 1));
        index++;
      } else {
        setIsTyping(false);
        clearInterval(interval);
      }
    }, 20);

    return () => clearInterval(interval);
  }, [scene.id, scene.description]);

  // Trigger lightning effect
  useEffect(() => {
    if (scene.atmosphere.lightning) {
      const visualizer = (window as any).gothicVisualizer;
      if (visualizer) {
        const interval = setInterval(() => {
          visualizer.triggerLightning();
        }, 5000 + Math.random() * 10000);

        return () => clearInterval(interval);
      }
    }
  }, [scene.atmosphere.lightning]);

  // Update fog intensity
  useEffect(() => {
    const visualizer = (window as any).gothicVisualizer;
    if (visualizer && scene.atmosphere.fog !== undefined) {
      visualizer.setFogIntensity(scene.atmosphere.fog);
    }
  }, [scene.atmosphere.fog]);

  return (
    <div className="story-panel fade-in">
      <h2 className="scene-title">{scene.title}</h2>
      <div className="scene-description">
        {displayedText}
        {isTyping && <span className="candle-flicker">▌</span>}
      </div>
      
      {!isTyping && !scene.isEnding && (
        <div className="choices-container">
          {scene.choices
            .filter(choice => choice.isVisible)
            .map(choice => (
              <ChoiceButton
                key={choice.id}
                choice={choice}
                onClick={() => onChoice(choice.id)}
              />
            ))}
        </div>
      )}

      {scene.isEnding && (
        <div className="ending-panel">
          <span className={`ending-type ${scene.endingType}`}>
            {scene.endingType?.toUpperCase()} ENDING
          </span>
        </div>
      )}
    </div>
  );
};

/**
 * Main Gothic Narrative UI Component
 */
export const GothicNarrativeUI: React.FC<{
  apiBaseUrl?: string;
}> = ({ apiBaseUrl = 'http://localhost:8000' }) => {
  const [scene, setScene] = useState<StoryScene | null>(null);
  const [playerState, setPlayerState] = useState<PlayerState>({
    currentScene: 'start',
    inventory: [],
    stats: { sanity: 100, courage: 50, knowledge: 0, suspicion: 0 },
    flags: {},
    choicesMade: [],
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch initial scene
  useEffect(() => {
    fetchScene('start');
  }, []);

  const fetchScene = async (sceneId: string) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${apiBaseUrl}/story/scene/${sceneId}`);
      if (!response.ok) {
        throw new Error('Failed to load scene');
      }

      const data = await response.json();
      setScene(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handleChoice = async (choiceId: string) => {
    if (!scene) return;

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `${apiBaseUrl}/story/choose?choice_id=${choiceId}&current_scene=${scene.id}`,
        { method: 'POST' }
      );

      if (!response.ok) {
        throw new Error('Failed to process choice');
      }

      const data = await response.json();
      setScene(data);
      
      // Update player state if provided
      if (data.playerState) {
        setPlayerState(data.playerState);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const restartStory = () => {
    fetchScene('start');
    setPlayerState({
      currentScene: 'start',
      inventory: [],
      stats: { sanity: 100, courage: 50, knowledge: 0, suspicion: 0 },
      flags: {},
      choicesMade: [],
    });
  };

  if (loading) {
    return (
      <div className="gothic-container" style={{ textAlign: 'center', paddingTop: '40vh' }}>
        <div className="loading-text">Loading...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="gothic-container" style={{ textAlign: 'center', paddingTop: '40vh' }}>
        <div className="gothic-text" style={{ color: 'var(--gothic-crimson)' }}>
          {error}
        </div>
        <button className="choice-button" onClick={() => fetchScene('start')} style={{ marginTop: '20px' }}>
          Restart
        </button>
      </div>
    );
  }

  return (
    <div className="gothic-container">
      {/* WebGL Canvas for atmospheric effects */}
      <canvas id="gothic-canvas" className="webgl-canvas" />
      
      {/* Atmospheric overlays */}
      <div className="fog-overlay" />
      <div className="vignette" />

      {/* Stats Panel */}
      <StatsPanel stats={playerState.stats} />

      {/* Main Scene */}
      {scene && <SceneDisplay scene={scene} onChoice={handleChoice} />}

      {/* Inventory Panel */}
      <InventoryPanel items={playerState.inventory} />

      {/* Ending Restart Button */}
      {scene?.isEnding && (
        <div style={{ textAlign: 'center', marginTop: '20px' }}>
          <button className="choice-button" onClick={restartStory}>
            Begin Again
          </button>
        </div>
      )}
    </div>
  );
};

export default GothicNarrativeUI;
