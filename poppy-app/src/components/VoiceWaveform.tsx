import React, { useEffect, useRef } from 'react';
import { View, StyleSheet, Animated, ViewStyle } from 'react-native';
import { Colors } from '../theme';

interface VoiceWaveformProps {
  waveform?: number[];
  isPlaying?: boolean;
  isRecording?: boolean;
  color?: string;
  barCount?: number;
  height?: number;
  style?: ViewStyle;
}

export const VoiceWaveform: React.FC<VoiceWaveformProps> = ({
  waveform,
  isPlaying = false,
  isRecording = false,
  color = Colors.primary,
  barCount = 30,
  height = 40,
  style,
}) => {
  const animatedValues = useRef(
    Array.from({ length: barCount }, () => new Animated.Value(0.3))
  ).current;

  useEffect(() => {
    if (isRecording || isPlaying) {
      const animations = animatedValues.map((anim, index) =>
        Animated.loop(
          Animated.sequence([
            Animated.timing(anim, {
              toValue: Math.random() * 0.7 + 0.3,
              duration: 150 + Math.random() * 200,
              useNativeDriver: false,
            }),
            Animated.timing(anim, {
              toValue: Math.random() * 0.3 + 0.1,
              duration: 150 + Math.random() * 200,
              useNativeDriver: false,
            }),
          ])
        )
      );
      Animated.stagger(30, animations).start();
      return () => animations.forEach(a => a.stop());
    } else if (waveform) {
      waveform.forEach((val, index) => {
        if (index < barCount) {
          Animated.timing(animatedValues[index], {
            toValue: val,
            duration: 300,
            useNativeDriver: false,
          }).start();
        }
      });
    }
  }, [isPlaying, isRecording]);

  return (
    <View style={[styles.container, { height }, style]}>
      {animatedValues.map((anim, index) => (
        <Animated.View
          key={index}
          style={[
            styles.bar,
            {
              backgroundColor: color,
              height: anim.interpolate({
                inputRange: [0, 1],
                outputRange: [4, height],
              }),
              opacity: anim.interpolate({
                inputRange: [0, 1],
                outputRange: [0.4, 1],
              }),
            },
          ]}
        />
      ))}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 2,
  },
  bar: {
    width: 3,
    borderRadius: 2,
    minHeight: 4,
  },
});
