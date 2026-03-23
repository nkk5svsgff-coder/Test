import React, { useState, useRef, useEffect } from 'react';
import {
  View,
  TouchableOpacity,
  Text,
  StyleSheet,
  Animated,
  Pressable,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { Colors, Typography, Shadows, Spacing } from '../theme';
import { VoiceWaveform } from './VoiceWaveform';

interface VoiceRecordButtonProps {
  onRecordComplete: (duration: number) => void;
  size?: number;
}

export const VoiceRecordButton: React.FC<VoiceRecordButtonProps> = ({
  onRecordComplete,
  size = 72,
}) => {
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const pulseAnim = useRef(new Animated.Value(1)).current;
  const glowAnim = useRef(new Animated.Value(0)).current;
  const timerRef = useRef<ReturnType<typeof setInterval>>(undefined);

  useEffect(() => {
    if (isRecording) {
      // Pulse animation
      Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, {
            toValue: 1.3,
            duration: 800,
            useNativeDriver: true,
          }),
          Animated.timing(pulseAnim, {
            toValue: 1,
            duration: 800,
            useNativeDriver: true,
          }),
        ])
      ).start();

      // Glow animation
      Animated.loop(
        Animated.sequence([
          Animated.timing(glowAnim, {
            toValue: 1,
            duration: 1000,
            useNativeDriver: false,
          }),
          Animated.timing(glowAnim, {
            toValue: 0,
            duration: 1000,
            useNativeDriver: false,
          }),
        ])
      ).start();

      // Timer
      timerRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1);
      }, 1000);
    } else {
      pulseAnim.setValue(1);
      glowAnim.setValue(0);
      if (timerRef.current) clearInterval(timerRef.current);
    }

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isRecording]);

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const handlePress = () => {
    if (isRecording) {
      setIsRecording(false);
      onRecordComplete(recordingTime);
      setRecordingTime(0);
    } else {
      setIsRecording(true);
    }
  };

  return (
    <View style={styles.container}>
      {isRecording && (
        <View style={styles.recordingInfo}>
          <VoiceWaveform
            isRecording={true}
            color={Colors.primary}
            height={32}
            barCount={20}
          />
          <Text style={styles.timer}>{formatTime(recordingTime)}</Text>
        </View>
      )}

      <View style={styles.buttonContainer}>
        <Animated.View
          style={[
            styles.pulseRing,
            {
              width: size + 24,
              height: size + 24,
              borderRadius: (size + 24) / 2,
              transform: [{ scale: pulseAnim }],
              opacity: isRecording ? 0.3 : 0,
              backgroundColor: Colors.primary,
            },
          ]}
        />
        <TouchableOpacity onPress={handlePress} activeOpacity={0.8}>
          <LinearGradient
            colors={
              isRecording
                ? [Colors.coral, Colors.primary] as [string, string]
                : Colors.gradientPrimary as unknown as [string, string]
            }
            style={[
              styles.button,
              {
                width: size,
                height: size,
                borderRadius: size / 2,
              },
              Shadows.glow,
            ]}
          >
            <Ionicons
              name={isRecording ? 'stop' : 'mic'}
              size={size * 0.4}
              color={Colors.white}
            />
          </LinearGradient>
        </TouchableOpacity>
      </View>

      <Text style={styles.hint}>
        {isRecording ? 'Tap to send' : 'Tap to record'}
      </Text>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    gap: Spacing.sm,
  },
  recordingInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.md,
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.sm,
    backgroundColor: Colors.primarySoft,
    borderRadius: 20,
  },
  timer: {
    ...Typography.labelLarge,
    color: Colors.primary,
  },
  buttonContainer: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  pulseRing: {
    position: 'absolute',
  },
  button: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  hint: {
    ...Typography.caption,
    color: Colors.gray,
  },
});
