import React, { useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Image,
  Keyboard,
  Modal,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  TouchableWithoutFeedback,
  View,
} from 'react-native';
import MapView, { Callout, Marker, MapPressEvent } from 'react-native-maps';
import * as Location from 'expo-location';
import * as ImagePicker from 'expo-image-picker';
import apiClient from '../api/client';

interface Coordinate {
  latitude: number;
  longitude: number;
}

interface DetectiveReportItem {
  id: string;
  latitude: number;
  longitude: number;
  problem_type: string;
  problem_type_display: string;
  description: string;
  photo: string | null;
  status: string;
}

const INITIAL_REGION = {
  latitude: 36.8969,
  longitude: 30.6553,
  latitudeDelta: 0.015,
  longitudeDelta: 0.015,
};

export default function DetectiveScreen() {
  const [selectedLocation, setSelectedLocation] = useState<Coordinate | null>(null);
  const [userLocation, setUserLocation] = useState<Coordinate | null>(null);
  const [reports, setReports] = useState<DetectiveReportItem[]>([]);
  const mapRef = useRef<MapView>(null);

  // Modal state'leri
  const [modalVisible, setModalVisible] = useState(false);
  const [description, setDescription] = useState('');
  const [imageUri, setImageUri] = useState('');
  const [imageBase64, setImageBase64] = useState('');
  const [loading, setLoading] = useState(false);

  const fetchReports = async () => {
    try {
      const response = await apiClient.get('detective/reports/');
      setReports(response.data.results ?? response.data);
    } catch (error) {
      console.error('Raporlar yüklenemedi:', error);
    }
  };

  useEffect(() => {
    fetchReports();
    (async () => {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') return;
      const position = await Location.getCurrentPositionAsync({});
      setUserLocation({
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
      });
    })();
  }, []);

  const goToUserLocation = async () => {
    const position = await Location.getCurrentPositionAsync({});
    mapRef.current?.animateToRegion(
      {
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
        latitudeDelta: 0.005,
        longitudeDelta: 0.005,
      },
      800,
    );
  };

  const handleMapPress = (event: MapPressEvent) => {
    setSelectedLocation(event.nativeEvent.coordinate);
  };

  const openImageOptions = () => {
    Alert.alert('Fotoğraf Ekle', 'Nasıl eklemek istersiniz?', [
      { text: 'Kamerayı Aç', onPress: takePhoto },
      { text: 'Galeriden Seç', onPress: pickImage },
      { text: 'İptal', style: 'cancel' },
    ]);
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
      setImageBase64(result.assets[0].base64 ?? '');
    }
  };

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
      setImageBase64(result.assets[0].base64 ?? '');
    }
  };

  const closeModal = () => {
    setModalVisible(false);
    setDescription('');
    setImageUri('');
    setImageBase64('');
  };

  const submitReport = async () => {
    if (!selectedLocation) return;

    setLoading(true);
    try {
      await apiClient.post('detective/reports/', {
        latitude: Number(selectedLocation?.latitude.toFixed(6)),
        longitude: Number(selectedLocation?.longitude.toFixed(6)),
        description: description,
        problem_type: 'OTHER',
        photo_base64: imageBase64,
      });
      Alert.alert('Başarılı', 'Çevre sorunu bildirildi, teşekkürler!');
      closeModal();
      setSelectedLocation(null);
      fetchReports();
    } catch (error: any) {
      const message = error?.response?.data
        ? JSON.stringify(error.response.data)
        : 'Bir hata oluştu.';
      Alert.alert('Hata', message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <MapView
        ref={mapRef}
        style={styles.map}
        initialRegion={INITIAL_REGION}
        showsUserLocation={true}
        showsMyLocationButton={false}
        onPress={handleMapPress}
      >
        {reports.map((report) => (
          <Marker
            key={report.id}
            coordinate={{
              latitude: Number(report.latitude),
              longitude: Number(report.longitude),
            }}
            pinColor="red"
          >
            <Callout tooltip>
              <View style={styles.callout}>
                <Text style={styles.calloutTitle}>
                  {report.problem_type_display ?? report.problem_type}
                </Text>
                {!!report.description && (
                  <Text style={styles.calloutDescription}>{report.description}</Text>
                )}
                {!!report.photo && (
                  <Image
                    source={{ uri: report.photo }}
                    style={styles.calloutImage}
                    resizeMode="cover"
                  />
                )}
              </View>
            </Callout>
          </Marker>
        ))}
        {selectedLocation && (
          <Marker coordinate={selectedLocation} />
        )}
      </MapView>

      <View style={styles.header}>
        <Text style={styles.headerTitle}>Çevre Dedektifi</Text>
        <Text style={styles.headerSub}>
          {selectedLocation
            ? 'Konum seçildi. Bildirmek için butona bas.'
            : 'Sorun bildirmek için haritaya dokun.'}
        </Text>
      </View>

      <TouchableOpacity style={styles.locateBtn} onPress={goToUserLocation}>
        <Text style={styles.locateBtnIcon}>🎯</Text>
      </TouchableOpacity>

      {selectedLocation && (
        <View style={styles.panel}>
          <View style={styles.panelCoords}>
            <Text style={styles.coordLabel}>Enlem</Text>
            <Text style={styles.coordValue}>{selectedLocation.latitude.toFixed(5)}</Text>
            <View style={styles.coordDivider} />
            <Text style={styles.coordLabel}>Boylam</Text>
            <Text style={styles.coordValue}>{selectedLocation.longitude.toFixed(5)}</Text>
          </View>
          <TouchableOpacity
            style={styles.reportBtn}
            onPress={() => setModalVisible(true)}
          >
            <Text style={styles.reportBtnText}>Bu Konumu Bildir</Text>
          </TouchableOpacity>
        </View>
      )}

      {/* Bildirim Modalı */}
      <Modal
        animationType="slide"
        transparent={true}
        visible={modalVisible}
        onRequestClose={closeModal}
      >
        <TouchableWithoutFeedback onPress={Keyboard.dismiss}>
          <View style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            <ScrollView showsVerticalScrollIndicator={false} keyboardShouldPersistTaps="handled">
              <Text style={styles.modalTitle}>Çevre Sorunu Bildir</Text>
              {selectedLocation && (
                <Text style={styles.modalCoords}>
                  📍 {selectedLocation.latitude.toFixed(5)}, {selectedLocation.longitude.toFixed(5)}
                </Text>
              )}

              <Text style={styles.fieldLabel}>Açıklama</Text>
              <TextInput
                style={styles.textArea}
                placeholder="Sorunu kısaca açıklayın..."
                placeholderTextColor="#bbb"
                multiline
                numberOfLines={4}
                value={description}
                onChangeText={setDescription}
              />

              <Text style={styles.fieldLabel}>Fotoğraf</Text>
              <TouchableOpacity style={styles.photoBtn} onPress={openImageOptions}>
                <Text style={styles.photoBtnIcon}>📷</Text>
                <Text style={styles.photoBtnText}>
                  {imageUri ? 'Fotoğrafı Değiştir' : 'Fotoğraf Ekle'}
                </Text>
              </TouchableOpacity>

              {imageUri ? (
                <View style={styles.previewContainer}>
                  <Image source={{ uri: imageUri }} style={styles.preview} />
                  <TouchableOpacity
                    style={styles.removeBtn}
                    onPress={() => { setImageUri(''); setImageBase64(''); }}
                  >
                    <Text style={styles.removeBtnText}>✕</Text>
                  </TouchableOpacity>
                </View>
              ) : null}

              <View style={styles.modalActions}>
                <TouchableOpacity style={styles.cancelBtn} onPress={closeModal}>
                  <Text style={styles.cancelBtnText}>İptal</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[styles.submitBtn, loading && styles.submitBtnDisabled]}
                  onPress={submitReport}
                  disabled={loading}
                >
                  {loading
                    ? <ActivityIndicator color="#fff" />
                    : <Text style={styles.submitBtnText}>Gönder</Text>
                  }
                </TouchableOpacity>
              </View>
            </ScrollView>
          </View>
          </View>
        </TouchableWithoutFeedback>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  map: {
    ...StyleSheet.absoluteFillObject,
  },

  // Üst başlık
  header: {
    position: 'absolute',
    top: 52,
    left: 16,
    right: 16,
    backgroundColor: 'rgba(255,255,255,0.93)',
    borderRadius: 14,
    paddingVertical: 12,
    paddingHorizontal: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 4,
  },
  headerTitle: {
    fontSize: 17,
    fontWeight: '700',
    color: '#1a1a1a',
  },
  headerSub: {
    fontSize: 13,
    color: '#666',
    marginTop: 2,
  },

  // Alt yüzen panel
  panel: {
    position: 'absolute',
    bottom: 32,
    left: 16,
    right: 16,
    backgroundColor: '#fff',
    borderRadius: 18,
    padding: 18,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: -2 },
    shadowOpacity: 0.1,
    shadowRadius: 12,
    elevation: 8,
  },
  panelCoords: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
    marginBottom: 14,
  },
  coordLabel: {
    fontSize: 11,
    color: '#aaa',
    fontWeight: '600',
    textTransform: 'uppercase',
  },
  coordValue: {
    fontSize: 13,
    color: '#333',
    fontWeight: '700',
    marginTop: 2,
  },
  coordDivider: {
    width: 1,
    height: 28,
    backgroundColor: '#eee',
  },
  reportBtn: {
    backgroundColor: '#4CAF50',
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
    shadowColor: '#4CAF50',
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.3,
    shadowRadius: 6,
    elevation: 4,
  },
  reportBtnText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '700',
  },

  // Callout baloncuğu
  callout: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 12,
    minWidth: 160,
    maxWidth: 200,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.15,
    shadowRadius: 8,
    elevation: 6,
  },
  calloutTitle: {
    fontSize: 13,
    fontWeight: '700',
    color: '#1a1a1a',
    marginBottom: 4,
  },
  calloutDescription: {
    fontSize: 12,
    color: '#555',
    marginBottom: 8,
  },
  calloutImage: {
    width: 150,
    height: 100,
    borderRadius: 8,
  },

  // Konumumu Bul butonu
  locateBtn: {
    position: 'absolute',
    right: 16,
    bottom: 200,
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: '#fff',
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.15,
    shadowRadius: 6,
    elevation: 5,
  },
  locateBtnIcon: {
    fontSize: 22,
  },

  // Modal
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.45)',
    justifyContent: 'flex-end',
  },
  modalCard: {
    backgroundColor: '#fff',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    padding: 24,
    maxHeight: '85%',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: -4 },
    shadowOpacity: 0.12,
    shadowRadius: 16,
    elevation: 12,
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#1a1a1a',
    marginBottom: 4,
  },
  modalCoords: {
    fontSize: 12,
    color: '#888',
    marginBottom: 20,
  },
  fieldLabel: {
    fontSize: 12,
    fontWeight: '600',
    color: '#555',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 8,
  },
  textArea: {
    backgroundColor: '#f7f8f7',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#e8e8e8',
    padding: 12,
    fontSize: 14,
    color: '#1a1a1a',
    minHeight: 100,
    textAlignVertical: 'top',
    marginBottom: 20,
  },
  photoBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: '#f7f8f7',
    borderRadius: 12,
    borderWidth: 1.5,
    borderColor: '#4CAF50',
    borderStyle: 'dashed',
    paddingVertical: 12,
    paddingHorizontal: 16,
    marginBottom: 14,
  },
  photoBtnIcon: {
    fontSize: 18,
  },
  photoBtnText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#4CAF50',
  },
  previewContainer: {
    position: 'relative',
    marginBottom: 20,
    alignSelf: 'flex-start',
  },
  preview: {
    width: 110,
    height: 110,
    borderRadius: 12,
  },
  removeBtn: {
    position: 'absolute',
    top: -8,
    right: -8,
    backgroundColor: '#F44336',
    borderRadius: 11,
    width: 22,
    height: 22,
    alignItems: 'center',
    justifyContent: 'center',
  },
  removeBtnText: {
    color: '#fff',
    fontSize: 10,
    fontWeight: '700',
  },
  modalActions: {
    flexDirection: 'row',
    gap: 12,
    marginTop: 4,
    marginBottom: 8,
  },
  cancelBtn: {
    flex: 1,
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
    backgroundColor: '#f0f0f0',
  },
  cancelBtnText: {
    fontSize: 15,
    fontWeight: '600',
    color: '#555',
  },
  submitBtn: {
    flex: 2,
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
    backgroundColor: '#4CAF50',
    shadowColor: '#4CAF50',
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.3,
    shadowRadius: 6,
    elevation: 4,
  },
  submitBtnDisabled: {
    opacity: 0.6,
  },
  submitBtnText: {
    fontSize: 15,
    fontWeight: '700',
    color: '#fff',
  },
});
