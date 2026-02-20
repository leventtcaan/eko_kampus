import React, { useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Image,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import apiClient from '../api/client';

const WASTE_CATEGORIES = ['PLASTIC', 'PAPER', 'GLASS', 'ORGANIC'];

export default function HomeScreen() {
  const [binId, setBinId] = useState('');
  const [wasteCategory, setWasteCategory] = useState('PLASTIC');
  const [loading, setLoading] = useState(false);
  const [imageUri, setImageUri] = useState<string | null>(null);
  const [imageBase64, setImageBase64] = useState<string | null>(null);

  const pickImage = async () => {
    const { status } = await ImagePicker.requestCameraPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert('İzin Gerekli', 'Kamera erişimi için izin vermeniz gerekiyor.');
      return;
    }

    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: true,
      quality: 0.5,
      base64: true,
    });

    if (!result.canceled && result.assets[0]) {
      setImageUri(result.assets[0].uri);
      setImageBase64(result.assets[0].base64 ?? null);
    }
  };

  const takePhoto = async () => {
    const { status } = await ImagePicker.requestCameraPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert('İzin Gerekli', 'Kamera erişimi için izin vermeniz gerekiyor.');
      return;
    }

    const result = await ImagePicker.launchCameraAsync({
      allowsEditing: true,
      quality: 0.5,
      base64: true,
    });

    if (!result.canceled && result.assets[0]) {
      setImageUri(result.assets[0].uri);
      setImageBase64(result.assets[0].base64 ?? null);
    }
  };

  const openImageOptions = () => {
    Alert.alert('Fotoğraf Ekle', 'Nasıl eklemek istersiniz?', [
      { text: 'Kamerayı Aç', onPress: takePhoto },
      { text: 'Galeriden Seç', onPress: pickImage },
      { text: 'İptal', style: 'cancel' },
    ]);
  };

  const submitReport = async () => {
    if (!binId.trim()) {
      Alert.alert('Hata', 'Lütfen kutu ID\'sini girin.');
      return;
    }

    setLoading(true);
    try {
      await apiClient.post('reports/create/', {
        bin: binId.trim(),
        waste_category: wasteCategory,
        verification_method: 'QR',
        latitude: '36.8969',
        longitude: '30.6553',
        client_timestamp: new Date().toISOString(),
        photo_base64: imageBase64,
      });
      Alert.alert('Başarılı', 'Atık bildirimi gönderildi!');
      setBinId('');
      setImageUri(null);
      setImageBase64(null);
    } catch (error: any) {
      const message =
        error?.response?.data
          ? JSON.stringify(error.response.data)
          : 'Bir hata oluştu.';
      Alert.alert('Hata', message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
      <Text style={styles.title}>Çöp At</Text>
      <Text style={styles.subtitle}>Atığını bildir, puan kazan.</Text>

      <Text style={styles.label}>Kutu ID</Text>
      <TextInput
        style={styles.input}
        placeholder="Kutu kodunu girin..."
        placeholderTextColor="#aaa"
        value={binId}
        onChangeText={setBinId}
        autoCapitalize="none"
      />

      <Text style={styles.label}>Atık Türü</Text>
      <View style={styles.categoryRow}>
        {WASTE_CATEGORIES.map((cat) => (
          <TouchableOpacity
            key={cat}
            style={[
              styles.categoryBtn,
              wasteCategory === cat && styles.categoryBtnActive,
            ]}
            onPress={() => setWasteCategory(cat)}
          >
            <Text
              style={[
                styles.categoryText,
                wasteCategory === cat && styles.categoryTextActive,
              ]}
            >
              {cat}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      <Text style={styles.label}>Fotoğraf</Text>
      <TouchableOpacity style={styles.photoBtn} onPress={openImageOptions}>
        <Text style={styles.photoBtnIcon}>📷</Text>
        <Text style={styles.photoBtnText}>
          {imageUri ? 'Fotoğrafı Değiştir' : 'Fotoğraf Çek / Seç'}
        </Text>
      </TouchableOpacity>

      {imageUri && (
        <View style={styles.previewContainer}>
          <Image source={{ uri: imageUri }} style={styles.preview} />
          <TouchableOpacity
            style={styles.removeBtn}
            onPress={() => { setImageUri(null); setImageBase64(null); }}
          >
            <Text style={styles.removeBtnText}>✕</Text>
          </TouchableOpacity>
        </View>
      )}

      <TouchableOpacity
        style={[styles.submitBtn, loading && styles.submitBtnDisabled]}
        onPress={submitReport}
        disabled={loading}
      >
        {loading ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={styles.submitText}>Çöpü At</Text>
        )}
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: 24,
    backgroundColor: '#f7f8f7',
    flexGrow: 1,
  },
  title: {
    fontSize: 26,
    fontWeight: '700',
    color: '#1a1a1a',
    marginTop: 16,
  },
  subtitle: {
    fontSize: 14,
    color: '#888',
    marginTop: 4,
    marginBottom: 32,
  },
  label: {
    fontSize: 13,
    fontWeight: '600',
    color: '#555',
    marginBottom: 8,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  input: {
    backgroundColor: '#fff',
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 15,
    color: '#1a1a1a',
    borderWidth: 1,
    borderColor: '#e0e0e0',
    marginBottom: 24,
  },
  categoryRow: {
    flexDirection: 'row',
    gap: 8,
    flexWrap: 'wrap',
    marginBottom: 28,
  },
  categoryBtn: {
    paddingVertical: 8,
    paddingHorizontal: 16,
    borderRadius: 20,
    backgroundColor: '#fff',
    borderWidth: 1.5,
    borderColor: '#d0d0d0',
  },
  categoryBtnActive: {
    backgroundColor: '#4CAF50',
    borderColor: '#4CAF50',
  },
  categoryText: {
    fontSize: 13,
    fontWeight: '600',
    color: '#666',
  },
  categoryTextActive: {
    color: '#fff',
  },
  photoBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    backgroundColor: '#fff',
    borderRadius: 12,
    borderWidth: 1.5,
    borderColor: '#4CAF50',
    borderStyle: 'dashed',
    paddingVertical: 14,
    paddingHorizontal: 18,
    marginBottom: 16,
  },
  photoBtnIcon: {
    fontSize: 20,
  },
  photoBtnText: {
    fontSize: 15,
    fontWeight: '600',
    color: '#4CAF50',
  },
  previewContainer: {
    position: 'relative',
    marginBottom: 24,
    alignSelf: 'flex-start',
  },
  preview: {
    width: 120,
    height: 120,
    borderRadius: 12,
  },
  removeBtn: {
    position: 'absolute',
    top: -8,
    right: -8,
    backgroundColor: '#F44336',
    borderRadius: 12,
    width: 24,
    height: 24,
    alignItems: 'center',
    justifyContent: 'center',
  },
  removeBtnText: {
    color: '#fff',
    fontSize: 11,
    fontWeight: '700',
  },
  submitBtn: {
    backgroundColor: '#4CAF50',
    borderRadius: 14,
    paddingVertical: 16,
    alignItems: 'center',
    shadowColor: '#4CAF50',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 5,
    marginTop: 8,
  },
  submitBtnDisabled: {
    opacity: 0.6,
  },
  submitText: {
    color: '#fff',
    fontSize: 17,
    fontWeight: '700',
  },
});
