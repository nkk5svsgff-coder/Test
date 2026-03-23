import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import { User, Match, VoiceMessage } from '../types';
import {
  currentUser as mockCurrentUser,
  discoverProfiles as mockProfiles,
  mockMatches,
  mockMessages,
  PHOTO_REVEAL_THRESHOLD,
} from '../data/mockData';

interface AppContextType {
  // Auth
  isAuthenticated: boolean;
  currentUser: User;
  login: () => void;
  logout: () => void;

  // Discovery
  profiles: User[];
  currentProfileIndex: number;
  swipeLike: () => void;
  swipePass: () => void;
  swipeSuperLike: () => void;

  // Matches
  matches: Match[];
  getMatchUser: (match: Match) => User | undefined;

  // Chat
  getMessages: (matchId: string) => VoiceMessage[];
  sendVoiceMessage: (matchId: string, duration: number) => void;

  // Recording
  isRecording: boolean;
  setIsRecording: (val: boolean) => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [currentUser] = useState<User>(mockCurrentUser);
  const [profiles] = useState<User[]>(mockProfiles);
  const [currentProfileIndex, setCurrentProfileIndex] = useState(0);
  const [matches, setMatches] = useState<Match[]>(mockMatches);
  const [messages, setMessages] = useState<Record<string, VoiceMessage[]>>(mockMessages);
  const [isRecording, setIsRecording] = useState(false);

  const login = useCallback(() => setIsAuthenticated(true), []);
  const logout = useCallback(() => setIsAuthenticated(false), []);

  const swipeLike = useCallback(() => {
    const profile = profiles[currentProfileIndex];
    if (!profile) return;

    // Simulate a match (30% chance)
    if (Math.random() < 0.3) {
      const newMatch: Match = {
        id: `match-${Date.now()}`,
        users: [currentUser.id, profile.id],
        createdAt: new Date(),
        messageCount: 0,
        photosRevealed: false,
        unreadCount: 0,
      };
      setMatches(prev => [newMatch, ...prev]);
    }
    setCurrentProfileIndex(prev => prev + 1);
  }, [currentProfileIndex, profiles, currentUser.id]);

  const swipePass = useCallback(() => {
    setCurrentProfileIndex(prev => prev + 1);
  }, []);

  const swipeSuperLike = useCallback(() => {
    const profile = profiles[currentProfileIndex];
    if (!profile) return;

    // Super like always matches
    const newMatch: Match = {
      id: `match-${Date.now()}`,
      users: [currentUser.id, profile.id],
      createdAt: new Date(),
      messageCount: 0,
      photosRevealed: false,
      unreadCount: 0,
    };
    setMatches(prev => [newMatch, ...prev]);
    setCurrentProfileIndex(prev => prev + 1);
  }, [currentProfileIndex, profiles, currentUser.id]);

  const getMatchUser = useCallback((match: Match): User | undefined => {
    const otherId = match.users.find(id => id !== currentUser.id);
    return profiles.find(u => u.id === otherId);
  }, [currentUser.id, profiles]);

  const getMessages = useCallback((matchId: string): VoiceMessage[] => {
    return messages[matchId] || [];
  }, [messages]);

  const sendVoiceMessage = useCallback((matchId: string, duration: number) => {
    const match = matches.find(m => m.id === matchId);
    if (!match) return;

    const otherUserId = match.users.find(id => id !== currentUser.id) || '';
    const newMessage: VoiceMessage = {
      id: `msg-${Date.now()}`,
      senderId: currentUser.id,
      receiverId: otherUserId,
      audioUrl: '',
      duration,
      timestamp: new Date(),
      isPlayed: false,
      waveform: Array.from({ length: 30 }, () => Math.random() * 0.8 + 0.1),
    };

    setMessages(prev => ({
      ...prev,
      [matchId]: [...(prev[matchId] || []), newMessage],
    }));

    const newCount = (match.messageCount || 0) + 1;
    setMatches(prev => prev.map(m =>
      m.id === matchId
        ? {
            ...m,
            lastMessage: newMessage,
            messageCount: newCount,
            photosRevealed: newCount >= PHOTO_REVEAL_THRESHOLD,
          }
        : m
    ));
  }, [matches, currentUser.id]);

  return (
    <AppContext.Provider
      value={{
        isAuthenticated,
        currentUser,
        login,
        logout,
        profiles,
        currentProfileIndex,
        swipeLike,
        swipePass,
        swipeSuperLike,
        matches,
        getMatchUser,
        getMessages,
        sendVoiceMessage,
        isRecording,
        setIsRecording,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export const useApp = (): AppContextType => {
  const context = useContext(AppContext);
  if (!context) throw new Error('useApp must be used within AppProvider');
  return context;
};
