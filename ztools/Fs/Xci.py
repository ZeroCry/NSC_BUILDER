from binascii import hexlify as hx, unhexlify as uhx
from Fs.Hfs0 import Hfs0
from Fs.Ticket import Ticket
from Fs.Nca import Nca
from Fs.File import File
import os
import Print
import Keys
import aes128
import Hex
import Title
import Titles
import Hex
import sq_tools
from struct import pack as pk, unpack as upk
from hashlib import sha256
import Fs.Type
import re
import pathlib
import Keys
import Config
import Print
from tqdm import tqdm





MEDIA_SIZE = 0x200

class GamecardInfo(File):
	def __init__(self, file = None):
		super(GamecardInfo, self).__init__()
		if file:
			self.open(file)
	
	def open(self, file, mode='rb', cryptoType = -1, cryptoKey = -1, cryptoCounter = -1):
		super(GamecardInfo, self).open(file, mode, cryptoType, cryptoKey, cryptoCounter)
		self.rewind()
		self.firmwareVersion = self.readInt64()
		self.accessControlFlags = self.readInt32()
		self.readWaitTime = self.readInt32()
		self.readWaitTime2 = self.readInt32()
		self.writeWaitTime = self.readInt32()
		self.writeWaitTime2 = self.readInt32()
		self.firmwareMode = self.readInt32()
		self.cupVersion = self.readInt32()
		self.empty1 = self.readInt32()
		self.updatePartitionHash = self.readInt64()
		self.cupId = self.readInt64()
		self.empty2 = self.read(0x38)
		
class GamecardCertificate(File):
	def __init__(self, file = None):
		super(GamecardCertificate, self).__init__()
		self.signature = None
		self.magic = None
		self.unknown1 = None
		self.unknown2 = None
		self.data = None
		
		if file:
			self.open(file)
			
	def open(self, file, mode = 'rb', cryptoType = -1, cryptoKey = -1, cryptoCounter = -1):
		super(GamecardCertificate, self).open(file, mode, cryptoType, cryptoKey, cryptoCounter)
		self.rewind()
		self.signature = self.read(0x100)
		self.magic = self.read(0x4)
		self.unknown1 = self.read(0x10)
		self.unknown2 = self.read(0xA)
		self.data = self.read(0xD6)
			
class Xci(File):
	def __init__(self, file = None):
		super(Xci, self).__init__()
		self.header = None
		self.signature = None
		self.magic = None
		self.secureOffset = None
		self.backupOffset = None
		self.titleKekIndex = None
		self.gamecardSize = None
		self.gamecardHeaderVersion = None
		self.gamecardFlags = None
		self.packageId = None
		self.validDataEndOffset = None
		self.gamecardInfo = None
		
		self.hfs0Offset = None
		self.hfs0HeaderSize = None
		self.hfs0HeaderHash = None
		self.hfs0InitialDataHash = None
		self.secureMode = None
		
		self.titleKeyFlag = None
		self.keyFlag = None
		self.normalAreaEndOffset = None
		
		self.gamecardInfo = None
		self.gamecardCert = None
		self.hfs0 = None
		
		if file:
			self.open(file)
		
	def readHeader(self):
	
		self.signature = self.read(0x100)
		self.magic = self.read(0x4)
		self.secureOffset = self.readInt32()
		self.backupOffset = self.readInt32()
		self.titleKekIndex = self.readInt8()
		self.gamecardSize = self.readInt8()
		self.gamecardHeaderVersion = self.readInt8()
		self.gamecardFlags = self.readInt8()
		self.packageId = self.readInt64()
		self.validDataEndOffset = self.readInt64()
		self.gamecardInfo = self.read(0x10)
		
		self.hfs0Offset = self.readInt64()
		self.hfs0HeaderSize = self.readInt64()
		self.hfs0HeaderHash = self.read(0x20)
		self.hfs0InitialDataHash = self.read(0x20)
		self.secureMode = self.readInt32()
		
		self.titleKeyFlag = self.readInt32()
		self.keyFlag = self.readInt32()
		self.normalAreaEndOffset = self.readInt32()
		
		self.gamecardInfo = GamecardInfo(self.partition(self.tell(), 0x70))
		self.gamecardCert = GamecardCertificate(self.partition(0x7000, 0x200))
		

	def open(self, path = None, mode = 'rb', cryptoType = -1, cryptoKey = -1, cryptoCounter = -1):
		r = super(Xci, self).open(path, mode, cryptoType, cryptoKey, cryptoCounter)
		self.readHeader()
		self.seek(0xF000)
		self.hfs0 = Hfs0(None, cryptoKey = None)
		self.partition(0xf000, None, self.hfs0, cryptoKey = None)

	def unpack(self, path):
		os.makedirs(path, exist_ok=True)

		for nspF in self.hfs0:
			filePath = os.path.abspath(path + '/' + nspF._path)
			f = open(filePath, 'wb')
			nspF.rewind()
			i = 0

			pageSize = 0x10000

			while True:
				buf = nspF.read(pageSize)
				if len(buf) == 0:
					break
				i += len(buf)
				f.write(buf)
			f.close()
			Print.info(filePath)
		
	def printInfo(self):
		maxDepth = 3
		indent = 0
		tabs = '\t' * indent
		Print.info('\n%sXCI Archive\n' % (tabs))
		super(Xci, self).printInfo(maxDepth, indent)
		
		Print.info(tabs + 'magic = ' + str(self.magic))
		Print.info(tabs + 'titleKekIndex = ' + str(self.titleKekIndex))
		
		Print.info(tabs + 'gamecardCert = ' + str(hx(self.gamecardCert.magic + self.gamecardCert.unknown1 + self.gamecardCert.unknown2 + self.gamecardCert.data)))
		self.hfs0.printInfo( indent)


	def copy_hfs0(self,ofolder,buffer,token):
		indent = 1
		tabs = '\t' * indent
		if token == "all":
			for nspF in self.hfs0:
				nspF.rewind()
				filename =  str(nspF._path)
				outfolder = str(ofolder)+'/'
				filepath = os.path.join(outfolder, filename)
				if not os.path.exists(outfolder):
					os.makedirs(outfolder)
				fp = open(filepath, 'w+b')
				nspF.rewind()
				Print.info(tabs + 'Copying: ' + str(filename))
				for data in iter(lambda: nspF.read(int(buffer)), ""):
					fp.write(data)
					fp.flush()
					if not data:
						break
				fp.close()
		else:
			for nspF in self.hfs0:
				if token == str(nspF._path):
					nspF.rewind()
					filename =  str(nspF._path)
					outfolder = str(ofolder)+'/'
					filepath = os.path.join(outfolder, filename)
					if not os.path.exists(outfolder):
						os.makedirs(outfolder)
					fp = open(filepath, 'w+b')
					nspF.rewind()
					Print.info(tabs + 'Copying: ' + str(filename))
					for data in iter(lambda: nspF.read(int(buffer)), ""):
						fp.write(data)
						fp.flush()
						if not data:
							break
					fp.close()

	def copy_ticket(self,ofolder,buffer,token):
		indent = 1
		tabs = '\t' * indent
		for nspF in self.hfs0:
			if token == str(nspF._path):
				for ticket in nspF:
					if type(ticket) == Ticket:
						ticket.rewind()
						data = ticket.read()
						filename =  str(ticket._path)
						outfolder = str(ofolder)+'/'
						filepath = os.path.join(outfolder, filename)
						if not os.path.exists(outfolder):
							os.makedirs(outfolder)
						fp = open(str(filepath), 'w+b')
						fp.write(data)
						fp.flush()

	def copy_cnmt(self,ofolder,buffer):
		for nspF in self.hfs0:
			if "secure" == str(nspF._path):
				for nca in nspF:
					if type(nca) == Nca:
						if 	str(nca.header.contentType) == 'Content.META':
							for f in nca:
								for file in f:
									nca.rewind()
									f.rewind()
									file.rewind()
									filename =  str(file._path)
									outfolder = str(ofolder)+'/'
									filepath = os.path.join(outfolder, filename)
									if not os.path.exists(outfolder):
										os.makedirs(outfolder)
									fp = open(filepath, 'w+b')
									nca.rewind()
									f.rewind()	
									file.rewind()								
									for data in iter(lambda:file.read(int(buffer)), ""):
										fp.write(data)
										fp.flush()
										if not data:
											break
									fp.close()
			
						
	def copy_other(self,ofolder,buffer,token):
		indent = 1
		tabs = '\t' * indent
		for nspF in self.hfs0:
			if token == str(nspF._path):
				for file in self:
					if type(file) == File:
						file.rewind()
						filename =  str(file._path)
						outfolder = str(ofolder)+'/'
						filepath = os.path.join(outfolder, filename)
						if not os.path.exists(outfolder):
							os.makedirs(outfolder)
						fp = open(filepath, 'w+b')
						file.rewind()
						for data in iter(lambda: file.read(int(buffer)), ""):
							fp.write(data)
							fp.flush()
							if not data:
								break
						fp.close()										
						
	def copy_root_hfs0(self,ofolder,buffer):
		indent = 1
		tabs = '\t' * indent
		target=self.hfs0
		target.rewind()
		filename = 'root.hfs0'
		outfolder = str(ofolder)+'/'
		filepath = os.path.join(outfolder, filename)
		if not os.path.exists(outfolder):
			os.makedirs(outfolder)
		fp = open(filepath, 'w+b')
		target.rewind()
		Print.info(tabs + 'Copying: ' + str(filename))
		for data in iter(lambda: target.read(int(buffer)), ""):
			fp.write(data)
			fp.flush()
			if not data:
				break
		fp.close()

#Copy nca files from secure 
	def copy_nca(self,ofolder,buffer,token,metapatch,keypatch,RSV_cap):
		if keypatch != 'false':
			keypatch = int(keypatch)
		indent = 1
		tabs = '\t' * indent
		for nspF in self.hfs0:
			if token == str(nspF._path):
				for nca in nspF:
					if type(nca) == Nca:
						nca.rewind()
						filename =  str(nca._path)
						outfolder = str(ofolder)+'/'
						filepath = os.path.join(outfolder, filename)
						if not os.path.exists(outfolder):
							os.makedirs(outfolder)
						fp = open(filepath, 'w+b')
						nca.rewind()
						Print.info(tabs + 'Copying: ' + str(filename))
						for data in iter(lambda: nca.read(int(buffer)), ""):
							fp.write(data)
							fp.flush()
							if not data:
								break
						fp.close()
						#///////////////////////////////////
						target = Fs.Nca(filepath, 'r+b')
						target.rewind()
						if keypatch != 'false':
							if keypatch < target.header.getCryptoType2():
								self.change_mkrev_nca(target, keypatch)
						target.close()		
						if metapatch == 'true':
							if 	str(nca.header.contentType) == 'Content.META':
								for pfs0 in nca:
									for cnmt in pfs0:
										check=str(cnmt._path)
										check=check[:-22]
									if check == 'AddOnContent':
										Print.info(tabs + '-------------------------------------')
										Print.info(tabs +'DLC -> No need to patch the meta' )
										Print.info(tabs + '-------------------------------------')
									else:	
										self.patch_meta(filepath,outfolder,RSV_cap)	
					
										
										
#Copy nca files from secure skipping deltas
	def copy_nca_nd(self,ofolder,buffer,metapatch,keypatch,RSV_cap):
		if keypatch != 'false':
			keypatch = int(keypatch)
		indent = 1
		tabs = '\t' * indent
		Print.info('Copying files: ')
		for nspF in self.hfs0:
			if str(nspF._path)=="secure":
				for nca in nspF:
					vfragment="false"
					if type(nca) == Nca:
						vfragment="false"
						if 	str(nca.header.contentType) == 'Content.DATA':
							for f in nca:
									for file in f:
										filename = str(file._path)
										if filename=="fragment":
											vfragment="true"			
						if str(vfragment)=="true":
							Print.info('Skipping delta fragment: ' + str(nca._path))
							continue
						else:			
							nca.rewind()
							filename =  str(nca._path)
							outfolder = str(ofolder)+'/'
							filepath = os.path.join(outfolder, filename)
							if not os.path.exists(outfolder):
								os.makedirs(outfolder)
							fp = open(filepath, 'w+b')
							nca.rewind()
							Print.info(tabs + 'Copying: ' + str(filename))
							for data in iter(lambda: nca.read(int(buffer)), ""):
								fp.write(data)
								fp.flush()
								if not data:
									break
							fp.close()
							#///////////////////////////////////
							target = Fs.Nca(filepath, 'r+b')
							target.rewind()
							if keypatch != 'false':
								if keypatch < target.header.getCryptoType2():
									self.change_mkrev_nca(target, keypatch)
							target.close()		
							if metapatch == 'true':
								if 	str(nca.header.contentType) == 'Content.META':
									for pfs0 in nca:
										for cnmt in pfs0:
											check=str(cnmt._path)
											check=check[:-22]
										if check == 'AddOnContent':
											Print.info(tabs + '-------------------------------------')
											Print.info(tabs +'DLC -> No need to patch the meta' )
											Print.info(tabs + '-------------------------------------')
										else:	
											self.patch_meta(filepath,outfolder,RSV_cap)	
						

#COPY AND CLEAN NCA FILES FROM SECURE AND PATCH NEEDED SYSTEM VERSION			
	def cr_tr_nca(self,ofolder,buffer,metapatch,keypatch,RSV_cap):
		if keypatch != 'false':
			keypatch = int(keypatch)
		indent = 1
		tabs = '\t' * indent
		for nspF in self.hfs0:
			if str(nspF._path)=="secure":
				for ticket in nspF:
					if type(ticket) == Ticket:
						masterKeyRev = ticket.getMasterKeyRevision()
						titleKeyDec = Keys.decryptTitleKey(ticket.getTitleKeyBlock().to_bytes(16, byteorder='big'), Keys.getMasterKeyIndex(masterKeyRev))
						rightsId = ticket.getRightsId()
						Print.info('rightsId =\t' + hex(rightsId))
						Print.info('titleKeyDec =\t' + str(hx(titleKeyDec)))
						Print.info('masterKeyRev =\t' + hex(masterKeyRev))
				for nca in nspF:
					if type(nca) == Nca:
						if nca.header.getRightsId() != 0:
							if nca.header.getCryptoType2() != masterKeyRev:
								pass
								raise IOError('Mismatched masterKeyRevs!')
				for nca in nspF:
					vfragment="false"
					if type(nca) == Nca:
						Print.info('Copying files: ')
						if nca.header.getRightsId() != 0:
							nca.rewind()
							filename =  str(nca._path)
							outfolder = str(ofolder)+'/'
							filepath = os.path.join(outfolder, filename)
							if not os.path.exists(outfolder):
								os.makedirs(outfolder)
							fp = open(filepath, 'w+b')
							nca.rewind()
							Print.info(tabs + 'Copying: ' + str(filename))
							for data in iter(lambda: nca.read(int(buffer)), ""):
								fp.write(data)
								fp.flush()
								if not data:
									break
							fp.close()							
							target = Nca(filepath, 'r+b')
							target.rewind()
							Print.info(tabs + 'Removing titlerights for ' + str(filename))
							Print.info(tabs + 'Writing masterKeyRev for %s, %d' % (str(nca._path),  masterKeyRev))
							crypto = aes128.AESECB(Keys.keyAreaKey(Keys.getMasterKeyIndex(masterKeyRev), nca.header.keyIndex))
							encKeyBlock = crypto.encrypt(titleKeyDec * 4)
							target.header.setRightsId(0)
							target.header.setKeyBlock(encKeyBlock)
							Hex.dump(encKeyBlock)	
							target.close()
							#///////////////////////////////////
							target = Fs.Nca(filepath, 'r+b')
							target.rewind()
							if keypatch != 'false':
								if keypatch < target.header.getCryptoType2():
									self.change_mkrev_nca(target, keypatch)
							target.close()									
						if nca.header.getRightsId() == 0:
							nca.rewind()
							filename =  str(nca._path)
							outfolder = str(ofolder)+'/'
							filepath = os.path.join(outfolder, filename)
							if not os.path.exists(outfolder):
								os.makedirs(outfolder)
							fp = open(filepath, 'w+b')
							nca.rewind()
							Print.info(tabs + 'Copying: ' + str(filename))
							for data in iter(lambda: nca.read(int(buffer)), ""):
								fp.write(data)
								fp.flush()
								if not data:
									break				
							fp.close()
							#///////////////////////////////////
							target = Fs.Nca(filepath, 'r+b')
							target.rewind()
							if keypatch != 'false':
								if keypatch < target.header.getCryptoType2():
									self.change_mkrev_nca(target, keypatch)
							target.close()									
							if metapatch == 'true':
								if 	str(nca.header.contentType) == 'Content.META':
									for pfs0 in nca:
										for cnmt in pfs0:
											check=str(cnmt._path)
											check=check[:-22]
										if check == 'AddOnContent':
											Print.info(tabs + '-------------------------------------')
											Print.info(tabs +'DLC -> No need to patch the meta' )
											Print.info(tabs + '-------------------------------------')
										else:	
											self.patch_meta(filepath,outfolder,RSV_cap)	
							


#COPY AND CLEAN NCA FILES FROM SECURE SKIPPING DELTAS AND PATCH NEEDED SYSTEM VERSION
	def cr_tr_nca_nd(self,ofolder,buffer,metapatch,keypatch,RSV_cap):
		if keypatch != 'false':
			keypatch = int(keypatch)
		indent = 1
		tabs = '\t' * indent
		for nspF in self.hfs0:
			if str(nspF._path)=="secure":
				for ticket in nspF:
					if type(ticket) == Ticket:
						masterKeyRev = ticket.getMasterKeyRevision()
						titleKeyDec = Keys.decryptTitleKey(ticket.getTitleKeyBlock().to_bytes(16, byteorder='big'), Keys.getMasterKeyIndex(masterKeyRev))
						rightsId = ticket.getRightsId()
						Print.info('rightsId =\t' + hex(rightsId))
						Print.info('titleKeyDec =\t' + str(hx(titleKeyDec)))
						Print.info('masterKeyRev =\t' + hex(masterKeyRev))
				for nca in nspF:
					if type(nca) == Nca:
						if nca.header.getRightsId() != 0:
							if nca.header.getCryptoType2() != masterKeyRev:
								pass
								raise IOError('Mismatched masterKeyRevs!')
				for nca in nspF:
					vfragment="false"
					if type(nca) == Nca:
						vfragment="false"
						if 	str(nca.header.contentType) == 'Content.DATA':
							for f in nca:
									for file in f:
										filename = str(file._path)
										if filename=="fragment":
											vfragment="true"
						if str(vfragment)=="true":
							Print.info('Skipping delta fragment: ' + str(nca._path))
							continue
						else:
							Print.info('Copying files: ')
							if nca.header.getRightsId() != 0:
								nca.rewind()
								filename =  str(nca._path)
								outfolder = str(ofolder)+'/'
								filepath = os.path.join(outfolder, filename)
								if not os.path.exists(outfolder):
									os.makedirs(outfolder)
								fp = open(filepath, 'w+b')
								nca.rewind()
								Print.info(tabs + 'Copying: ' + str(filename))
								for data in iter(lambda: nca.read(int(buffer)), ""):
									fp.write(data)
									fp.flush()
									if not data:
										break
								fp.close()
								target = Nca(filepath, 'r+b')
								target.rewind()
								Print.info(tabs + 'Removing titlerights for ' + str(filename))
								Print.info(tabs + 'Writing masterKeyRev for %s, %d' % (str(nca._path),  masterKeyRev))
								crypto = aes128.AESECB(Keys.keyAreaKey(Keys.getMasterKeyIndex(masterKeyRev), nca.header.keyIndex))
								encKeyBlock = crypto.encrypt(titleKeyDec * 4)
								target.header.setRightsId(0)
								target.header.setKeyBlock(encKeyBlock)
								Hex.dump(encKeyBlock)	
								target.close()
								#///////////////////////////////////
								target = Fs.Nca(filepath, 'r+b')
								target.rewind()
								if keypatch != 'false':
									if keypatch < target.header.getCryptoType2():
										self.change_mkrev_nca(target, keypatch)
								target.close()										
							if nca.header.getRightsId() == 0:
								nca.rewind()
								filename =  str(nca._path)
								outfolder = str(ofolder)+'/'
								filepath = os.path.join(outfolder, filename)
								if not os.path.exists(outfolder):
									os.makedirs(outfolder)
								fp = open(filepath, 'w+b')
								nca.rewind()
								Print.info(tabs + 'Copying: ' + str(filename))
								for data in iter(lambda: nca.read(int(buffer)), ""):
									fp.write(data)
									fp.flush()
									if not data:
										break
								fp.close()
								#///////////////////////////////////
								target = Fs.Nca(filepath, 'r+b')
								target.rewind()
								if keypatch != 'false':
									if keypatch < target.header.getCryptoType2():
										self.change_mkrev_nca(target, keypatch)
								target.close()										
								if metapatch == 'true':
									if 	str(nca.header.contentType) == 'Content.META':
										for pfs0 in nca:
											for cnmt in pfs0:
												check=str(cnmt._path)
												check=check[:-22]
											if check == 'AddOnContent':
												Print.info(tabs + '-------------------------------------')
												Print.info(tabs +'DLC -> No need to patch the meta' )
												Print.info(tabs + '-------------------------------------')
											else:	
												self.patch_meta(filepath,outfolder,RSV_cap)	
		
#///////////////////////////////////////////////////								
# Change MKREV_NCA
#///////////////////////////////////////////////////						
		
	def change_mkrev_nca(self, nca, newMasterKeyRev):
	
		indent = 2
		tabs = '\t' * indent
		indent2 = 3
		tabs2 = '\t' * indent2
		
		masterKeyRev = nca.header.getCryptoType2()	

		if type(nca) == Nca:
			if nca.header.getCryptoType2() != newMasterKeyRev:
				Print.info(tabs + '-----------------------------------')
				Print.info(tabs + 'Changing keygeneration from %d to %s' % ( nca.header.getCryptoType2(), str(newMasterKeyRev)))
				Print.info(tabs + '-----------------------------------')
				encKeyBlock = nca.header.getKeyBlock()
				if sum(encKeyBlock) != 0:
					key = Keys.keyAreaKey(Keys.getMasterKeyIndex(masterKeyRev), nca.header.keyIndex)
					Print.info(tabs2 + '+ decrypting with %s (%d, %d)' % (str(hx(key)), Keys.getMasterKeyIndex(masterKeyRev), nca.header.keyIndex))
					crypto = aes128.AESECB(key)
					decKeyBlock = crypto.decrypt(encKeyBlock)
					key = Keys.keyAreaKey(Keys.getMasterKeyIndex(newMasterKeyRev), nca.header.keyIndex)
					Print.info(tabs2 + '+ encrypting with %s (%d, %d)' % (str(hx(key)), Keys.getMasterKeyIndex(newMasterKeyRev), nca.header.keyIndex))
					crypto = aes128.AESECB(key)
					reEncKeyBlock = crypto.encrypt(decKeyBlock)
					nca.header.setKeyBlock(reEncKeyBlock)
				if newMasterKeyRev >= 3:
					nca.header.setCryptoType(2)
					nca.header.setCryptoType2(newMasterKeyRev)
				else:
					nca.header.setCryptoType(newMasterKeyRev)
					nca.header.setCryptoType2(0)	
					Print.info(tabs2 + 'DONE')					
	
#///////////////////////////////////////////////////								
#PATCH META FUNCTION
#///////////////////////////////////////////////////	
	def patch_meta(self,filepath,outfolder,RSV_cap):
		indent = 1
		tabs = '\t' * indent	
		Print.info(tabs + '-------------------------------------')
		Print.info(tabs + 'Checking meta: ')
		meta_nca = Fs.Nca(filepath, 'r+b')
		keygen=meta_nca.header.getCryptoType2()
		RSV=meta_nca.get_req_system()		
		RSVmin=sq_tools.getMinRSV(keygen,RSV)
		RSVmax=sq_tools.getTopRSV(keygen,RSV)		
		if 	RSV > RSVmin:
			if RSVmin >= RSV_cap:
				meta_nca.write_req_system(RSVmin)
			else:
				if keygen < 4:
					if RSV > RSVmax:
						meta_nca.write_req_system(RSV_cap)		
				else:
					meta_nca.write_req_system(RSV_cap)	
			meta_nca.flush()
			meta_nca.close()
			Print.info(tabs + 'Updating cnmt hashes: ')
			############################
			meta_nca = Fs.Nca(filepath, 'r+b')
			sha=meta_nca.calc_pfs0_hash()
			meta_nca.flush()
			meta_nca.close()
			meta_nca = Fs.Nca(filepath, 'r+b')
			meta_nca.set_pfs0_hash(sha)
			meta_nca.flush()
			meta_nca.close()
			############################
			meta_nca = Fs.Nca(filepath, 'r+b')
			sha2=meta_nca.calc_htable_hash()
			meta_nca.flush()
			meta_nca.close()						
			meta_nca = Fs.Nca(filepath, 'r+b')
			meta_nca.header.set_htable_hash(sha2)
			meta_nca.flush()
			meta_nca.close()
			########################
			meta_nca = Fs.Nca(filepath, 'r+b')
			sha3=meta_nca.header.calculate_hblock_hash()
			meta_nca.flush()
			meta_nca.close()						
			meta_nca = Fs.Nca(filepath, 'r+b')
			meta_nca.header.set_hblock_hash(sha3)
			meta_nca.flush()
			meta_nca.close()
			########################
			with open(filepath, 'r+b') as file:			
				nsha=sha256(file.read()).hexdigest()
			newname=nsha[:32] + '.cnmt.nca'				
			Print.info(tabs +'New name: ' + newname )
			dir=os.path.dirname(os.path.abspath(filepath))
			newpath=dir+ '/' + newname
			os.rename(filepath, newpath)
			Print.info(tabs + '-------------------------------------')
		else:
			Print.info(tabs +'-> No need to patch the meta' )
			Print.info(tabs + '-------------------------------------')								
		
#Check if titlerights			
	def trights_set(self):
		for nspF in self.hfs0:
			if str(nspF._path)=="secure":
				for nca in nspF:
					if type(nca) == Nca:	
						if nca.header.getRightsId() != 0:
							return 'TRUE'	
				return 'FALSE'							
		
#Check if exists ticket		
	def exist_ticket(self):
		for nspF in self.hfs0:
			if str(nspF._path)=="secure":
				for ticket in nspF:
					if type(ticket) == Ticket:
						return 'TRUE'	
				return 'FALSE'			
		

#READ CNMT FILE WITHOUT EXTRACTION	
	def read_cnmt(self):
		for nspF in self.hfs0:
			if str(nspF._path)=="secure":
				for nca in nspF:
					if type(nca) == Nca:
						if 	str(nca.header.contentType) == 'Content.META':
							for f in nca:
								for cnmt in f:
									nca.rewind()
									f.rewind()
									cnmt.rewind()
									titleid=cnmt.readInt64()
									titleversion = cnmt.read(0x4)
									cnmt.rewind()
									cnmt.seek(0xE)
									offset=cnmt.readInt16()
									content_entries=cnmt.readInt16()
									meta_entries=cnmt.readInt16()
									cnmt.rewind()
									cnmt.seek(0x20)
									original_ID=cnmt.readInt64()
									min_sversion=cnmt.readInt32()
									end_of_emeta=cnmt.readInt32()	
									Print.info('')	
									Print.info('...........................................')								
									Print.info('Reading: ' + str(cnmt._path))
									Print.info('...........................................')
									Print.info('titleid = ' + str(hx(titleid.to_bytes(8, byteorder='big'))))
									Print.info('version = ' + str(int.from_bytes(titleversion, byteorder='little')))
									Print.info('Table offset = '+ str(hx((offset+0x20).to_bytes(2, byteorder='big'))))
									Print.info('number of content = '+ str(content_entries))
									Print.info('number of meta entries = '+ str(meta_entries))
									Print.info('Application id\Patch id = ' + str(hx(original_ID.to_bytes(8, byteorder='big'))))
									content_name=str(cnmt._path)
									content_name=content_name[:-22]				
									if content_name == 'AddOnContent':
										Print.info('RequiredUpdateNumber = ' + str(min_sversion))
									if content_name != 'AddOnContent':
										Print.info('RequiredSystemVersion = ' + str(min_sversion))
									cnmt.rewind()
									cnmt.seek(0x20+offset)
									for i in range(content_entries):
										Print.info('........................')							
										Print.info('Content number ' + str(i+1))
										Print.info('........................')
										vhash = cnmt.read(0x20)
										Print.info('hash =\t' + str(hx(vhash)))
										NcaId = cnmt.read(0x10)
										Print.info('NcaId =\t' + str(hx(NcaId)))
										size = cnmt.read(0x6)
										Print.info('Size =\t' + str(int.from_bytes(size, byteorder='little')))
										ncatype = cnmt.read(0x1)
										Print.info('ncatype = ' + str(int.from_bytes(ncatype, byteorder='little')))
										unknown = cnmt.read(0x1)			
									
#///////////////////////////////////////////////////								
#SPLIT MULTI-CONTENT XCI IN FOLDERS
#///////////////////////////////////////////////////	
	def splitter_read(self,ofolder,buffer,pathend):
		for nspF in self.hfs0:
			if str(nspF._path)=="secure":
				for nca in nspF:
					if type(nca) == Nca:
						if 	str(nca.header.contentType) == 'Content.META':
							for f in nca:
								for cnmt in f:		
									nca.rewind()
									f.rewind()
									cnmt.rewind()
									titleid=cnmt.readInt64()
									titleversion = cnmt.read(0x4)
									cnmt.rewind()
									cnmt.seek(0xE)
									offset=cnmt.readInt16()
									content_entries=cnmt.readInt16()
									meta_entries=cnmt.readInt16()
									cnmt.rewind()
									cnmt.seek(0x20)
									original_ID=cnmt.readInt64()
									min_sversion=self.readInt32()
									end_of_emeta=self.readInt32()	
									target=str(nca._path)
									contentname = self.splitter_get_title(target,offset,content_entries,original_ID)
									cnmt.rewind()
									cnmt.seek(0x20+offset)
									titleid2 = str(hx(titleid.to_bytes(8, byteorder='big'))) 	
									titleid2 = titleid2[2:-1]
									Print.info('-------------------------------------')
									Print.info('Detected content: ' + str(titleid2))	
									Print.info('-------------------------------------')							
									for i in range(content_entries):
										vhash = cnmt.read(0x20)
										NcaId = cnmt.read(0x10)
										size = cnmt.read(0x6)
										ncatype = cnmt.read(0x1)
										unknown = cnmt.read(0x1)		
									#**************************************************************	
										version=str(int.from_bytes(titleversion, byteorder='little'))
										version='[v'+version+']'
										titleid3 ='['+ titleid2+']'
										nca_name=str(hx(NcaId))
										nca_name=nca_name[2:-1]+'.nca'
										ofolder2 = ofolder+ '/'+contentname+' '+ titleid3+' '+version+'/'+pathend
										self.splitter_copy(ofolder2,buffer,nca_name)
									nca_meta=str(nca._path)
									self.splitter_copy(ofolder2,buffer,nca_meta)
									self.splitter_tyc(ofolder2,titleid2)
		dirlist=os.listdir(ofolder)
		textpath = os.path.join(ofolder, 'dirlist.txt')
		with open(textpath, 'a') as tfile:		
			for folder in dirlist:
				item = os.path.join(ofolder, folder)
				tfile.write(item + '\n')

	
		indent = 1
		tabs = '\t' * indent
		token='secure'
		for nspF in self.hfs0:
			if token == str(nspF._path):
				for nca in nspF:
					if type(nca) == Nca:
						if nca_name == str(nca._path):
							nca.rewind()
							filename =  str(nca._path)
							outfolder = str(ofolder)+'/'
							filepath = os.path.join(outfolder, filename)
							if not os.path.exists(outfolder):
								os.makedirs(outfolder)
							fp = open(filepath, 'w+b')
							nca.rewind()
							Print.info(tabs + 'Copying: ' + str(filename))
							for data in iter(lambda: nca.read(int(buffer)), ""):
								fp.write(data)
								fp.flush()
								if not data:
									break
							fp.close()
	
	def splitter_copy(self,ofolder,buffer,nca_name):
		indent = 1
		tabs = '\t' * indent
		token='secure'
		for nspF in self.hfs0:
			if token == str(nspF._path):
				for nca in nspF:
					if type(nca) == Nca:
						if nca_name == str(nca._path):	
							nca.rewind()
							filename =  str(nca._path)
							outfolder = str(ofolder)+'/'
							filepath = os.path.join(outfolder, filename)
							if not os.path.exists(outfolder):
								os.makedirs(outfolder)
							fp = open(filepath, 'w+b')
							nca.rewind()
							Print.info(tabs + 'Copying: ' + str(filename))
							for data in iter(lambda: nca.read(int(buffer)), ""):
								fp.write(data)
								fp.flush()
								if not data:
									break
							fp.close()

	def splitter_tyc(self,ofolder,titleid):
		indent = 1
		tabs = '\t' * indent
		token='secure'
		for nspF in self.hfs0:
			if token == str(nspF._path):
				for ticket in nspF:		
					if type(ticket) == Ticket:
						tik_id = str(ticket._path)
						tik_id =tik_id[:-20]
						if titleid == tik_id:
							ticket.rewind()
							data = ticket.read()
							filename =  str(ticket._path)
							outfolder = str(ofolder)+'/'
							filepath = os.path.join(outfolder, filename)
							if not os.path.exists(outfolder):
								os.makedirs(outfolder)
							fp = open(str(filepath), 'w+b')
							Print.info(tabs + 'Copying: ' + str(filename))
							fp.write(data)
							fp.flush()
							fp.close()
		for nspF in self.hfs0:
			if token == str(nspF._path):
				for cert in nspF:				
					if cert._path.endswith('.cert'):
						cert_id = str(cert._path)
						cert_id =cert_id[:-21]
						if titleid == cert_id:				
							cert.rewind()
							data = cert.read()
							filename =  str(cert._path)
							outfolder = str(ofolder)+'/'
							filepath = os.path.join(outfolder, filename)
							if not os.path.exists(outfolder):
								os.makedirs(outfolder)
							fp = open(str(filepath), 'w+b')
							Print.info(tabs + 'Copying: ' + str(filename))
							fp.write(data)
							fp.flush()
							fp.close()
		
	def splitter_get_title(self,target,offset,content_entries,original_ID):
		content_type=''
		token='secure'		
		for nspF in self.hfs0:
			if token == str(nspF._path):
				for nca in nspF:
					if type(nca) == Nca:
						if target ==  str(nca._path):
							for f in nca:
								for cnmt in f:
									nca.rewind()
									f.rewind()
									cnmt.rewind()					
									cnmt.seek(0x20+offset)	
									nca_name='false'
									for i in range(content_entries):
										vhash = cnmt.read(0x20)
										NcaId = cnmt.read(0x10)
										size = cnmt.read(0x6)
										ncatype = cnmt.read(0x1)
										unknown = cnmt.read(0x1)
										ncatype2 = int.from_bytes(ncatype, byteorder='little')
										if ncatype2 == 3:
											nca_name=str(hx(NcaId))
											nca_name=nca_name[2:-1]+'.nca'
											content_name=str(cnmt._path)
											content_name=content_name[:-22]
											if content_name == 'Patch':
												content_type=' [UPD]'
		if nca_name=='false':
			for nspF in self.hfs0:
				if token == str(nspF._path):
					for nca in nspF:		
						if type(nca) == Nca:
							if 	str(nca.header.contentType) == 'Content.META':
								for f in nca:
									for cnmt in f:
										cnmt.rewind()
										testID=cnmt.readInt64()
										if 	testID == original_ID:
											nca.rewind()
											f.rewind()								
											titleid=cnmt.readInt64()
											titleversion = cnmt.read(0x4)
											cnmt.rewind()
											cnmt.seek(0xE)
											offset=cnmt.readInt16()
											content_entries=cnmt.readInt16()
											meta_entries=cnmt.readInt16()
											cnmt.rewind()
											cnmt.seek(0x20)
											original_ID=cnmt.readInt64()
											min_sversion=self.readInt32()
											end_of_emeta=self.readInt32()	
											target=str(nca._path)
											contentname = self.splitter_get_title(target,offset,content_entries,original_ID)
											cnmt.rewind()
											cnmt.seek(0x20+offset)								
											for i in range(content_entries):
												vhash = cnmt.read(0x20)
												NcaId = cnmt.read(0x10)
												size = cnmt.read(0x6)
												ncatype = cnmt.read(0x1)
												unknown = cnmt.read(0x1)
												ncatype2 = int.from_bytes(ncatype, byteorder='little')
												if ncatype2 == 3:
													nca_name=str(hx(NcaId))
													nca_name=nca_name[2:-1]+'.nca'
													content_type=' [DLC]'
		title='DLC'
		for nspF in self.hfs0:
			if token == str(nspF._path):
				for nca in nspF:		
					if type(nca) == Nca:
						if nca_name == str(nca._path):
							for f in nca:
								nca.rewind()
								f.rewind()	
								f.seek(0x14200)
								title = f.read(0x200)		
								title = title.split(b'\0', 1)[0].decode('utf-8')
								title = (re.sub(r'[\/\\\:\*\?\"\<\>\|\.\s™©®()\~]+', ' ', title))
								title = title + content_type
		return(title)
												
		

#///////////////////////////////////////////////////								
#PREPARE BASE CONTENT TO UPDATE IT
#///////////////////////////////////////////////////	
	def updbase_read(self,ofolder,buffer,cskip):
		for nspF in self.hfs0:
			if str(nspF._path)=="secure":
				for nca in nspF:
					if type(nca) == Nca:
						if 	str(nca.header.contentType) == 'Content.META':
							for f in nca:
								for cnmt in f:	
									content_name=str(cnmt._path)
									content_name=content_name[:-22]
									if content_name == 'Patch':
										if cskip == 'upd':
											continue
										if cskip == 'both':
											continue
									if content_name == 'AddOnContent':
										if cskip == 'dlc':
											continue
										if cskip == 'both':
											continue															
									nca.rewind()
									f.rewind()
									cnmt.rewind()
									titleid=cnmt.readInt64()
									titleversion = cnmt.read(0x4)
									cnmt.rewind()
									cnmt.seek(0xE)
									offset=cnmt.readInt16()
									content_entries=cnmt.readInt16()
									meta_entries=cnmt.readInt16()
									cnmt.rewind()
									cnmt.seek(0x20)
									original_ID=cnmt.readInt64()
									min_sversion=self.readInt32()
									end_of_emeta=self.readInt32()	
									target=str(nca._path)
									cnmt.rewind()
									cnmt.seek(0x20+offset)
									titleid2 = str(hx(titleid.to_bytes(8, byteorder='big'))) 	
									titleid2 = titleid2[2:-1]
									Print.info('-------------------------------------')
									Print.info('Copying content: ' + str(titleid2))	
									Print.info('-------------------------------------')							
									for i in range(content_entries):
										vhash = cnmt.read(0x20)
										NcaId = cnmt.read(0x10)
										size = cnmt.read(0x6)
										ncatype = cnmt.read(0x1)
										unknown = cnmt.read(0x1)		
									#**************************************************************	
										version=str(int.from_bytes(titleversion, byteorder='little'))
										version='[v'+version+']'
										titleid3 ='['+ titleid2+']'
										nca_name=str(hx(NcaId))
										nca_name=nca_name[2:-1]+'.nca'
										self.updbase_copy(ofolder,buffer,nca_name)
									nca_meta=str(nca._path)
									self.updbase_copy(ofolder,buffer,nca_meta)
									self.updbase_tyc(ofolder,titleid2)
									
	def updbase_copy(self,ofolder,buffer,nca_name):
		indent = 1
		tabs = '\t' * indent
		token='secure'
		for nspF in self.hfs0:
			if token == str(nspF._path):
				for nca in nspF:
					if type(nca) == Nca:
						if nca_name == str(nca._path):	
							nca.rewind()
							filename =  str(nca._path)
							outfolder = str(ofolder)+'/'
							filepath = os.path.join(outfolder, filename)
							if not os.path.exists(outfolder):
								os.makedirs(outfolder)
							fp = open(filepath, 'w+b')
							nca.rewind()
							Print.info(tabs + 'Copying: ' + str(filename))
							for data in iter(lambda: nca.read(int(buffer)), ""):
								fp.write(data)
								fp.flush()
								if not data:
									break
							fp.close()

	def updbase_tyc(self,ofolder,titleid):
		indent = 1
		tabs = '\t' * indent
		token='secure'
		for nspF in self.hfs0:
			if token == str(nspF._path):
				for ticket in nspF:		
					if type(ticket) == Ticket:
						tik_id = str(ticket._path)
						tik_id =tik_id[:-20]
						if titleid == tik_id:
							ticket.rewind()
							data = ticket.read()
							filename =  str(ticket._path)
							outfolder = str(ofolder)+'/'
							filepath = os.path.join(outfolder, filename)
							if not os.path.exists(outfolder):
								os.makedirs(outfolder)
							fp = open(str(filepath), 'w+b')
							Print.info(tabs + 'Copying: ' + str(filename))
							fp.write(data)
							fp.flush()
							fp.close()
		for nspF in self.hfs0:
			if token == str(nspF._path):
				for cert in nspF:				
					if cert._path.endswith('.cert'):
						cert_id = str(cert._path)
						cert_id =cert_id[:-21]
						if titleid == cert_id:				
							cert.rewind()
							data = cert.read()
							filename =  str(cert._path)
							outfolder = str(ofolder)+'/'
							filepath = os.path.join(outfolder, filename)
							if not os.path.exists(outfolder):
								os.makedirs(outfolder)
							fp = open(str(filepath), 'w+b')
							Print.info(tabs + 'Copying: ' + str(filename))
							fp.write(data)
							fp.flush()
							fp.close()
										
#GET VERSION NUMBER FROM CNMT							
	def get_cnmt_verID(self):
		for nspF in self.hfs0:
			if str(nspF._path)=="secure":
				for nca in nspF:
					if type(nca) == Nca:
						if 	str(nca.header.contentType) == 'Content.META':
							for f in nca:
								for cnmt in f:
									nca.rewind()
									f.rewind()
									cnmt.rewind()
									cnmt.seek(0x8)
									titleversion = cnmt.read(0x4)
									Print.info(str(int.from_bytes(titleversion, byteorder='little')))	
									
#SIMPLE FILE-LIST			
	def print_file_list(self):
		for nspF in self.hfs0:
			if str(nspF._path)=="secure":
				for nca in nspF:
					if type(nca) == Nca:
						if nca._path.endswith('.cnmt.nca'):
							continue
						filename = str(nca._path)
						Print.info(str(filename))
		for nspF in self.hfs0:
			if str(nspF._path)=="secure":
				for nca in nspF:
					if type(nca) == Nca:
						if nca._path.endswith('.cnmt.nca'):
							filename = str(nca._path)
							Print.info(str(filename))
		for nspF in self.hfs0:
			if str(nspF._path)=="secure":
				for file in nspF:
					if type(file) != Nca:
						filename =  str(file._path)
						Print.info(str(filename))									

#///////////////////////////////////////////////////								
#INFO ABOUT UPD REQUIREMENTS
#///////////////////////////////////////////////////	
	def print_fw_req(self):
		for nspF in self.hfs0:
			if str(nspF._path)=="secure":
				for nca in nspF:
					if type(nca) == Nca:
						if 	str(nca.header.contentType) == 'Content.META':
							for f in nca:
								for cnmt in f:
									nca.rewind()
									f.rewind()
									cnmt.rewind()
									titleid=cnmt.readInt64()
									titleversion = cnmt.read(0x4)
									cnmt.rewind()
									cnmt.seek(0xE)
									offset=cnmt.readInt16()
									content_entries=cnmt.readInt16()
									meta_entries=cnmt.readInt16()
									cnmt.rewind()
									cnmt.seek(0x20)
									original_ID=cnmt.readInt64()
									RSversion=cnmt.readInt32()
									Emeta=cnmt.readInt32()
									target=str(nca._path)
									contentname = self.inf_get_title(target,offset,content_entries,original_ID)
									cnmt.rewind()
									cnmt.seek(0x20+offset)
									titleid2 = str(hx(titleid.to_bytes(8, byteorder='big'))) 	
									titleid2 = titleid2[2:-1]
									version=str(int.from_bytes(titleversion, byteorder='little'))
									keygen=nca.header.getCryptoType2()					
									MinRSV=sq_tools.getMinRSV(keygen,RSversion)
									FW_rq=sq_tools.getFWRangeKG(keygen)
									RSV_rq=sq_tools.getFWRangeRSV(RSversion)									
									RSV_rq_min=sq_tools.getFWRangeRSV(MinRSV)
									content_name=str(cnmt._path)
									content_name=content_name[:-22]
									if content_name == 'Patch':
										content_type='Update'
										reqtag='- RequiredSystemVersion: '										
									if content_name == 'AddOnContent':
										content_type='DLC'
										reqtag='- RequiredUpdateNumber: '
									if content_name == 'Application':
										content_type='Base Game or Application'
										reqtag='- RequiredSystemVersion: '	
									Print.info('-------------------------------------')
									Print.info('Detected content: ' + str(titleid2))	
									Print.info('-------------------------------------')	
									if content_name != 'AddOnContent':							
										Print.info("- Name: " + contentname)
									v_number=int(int(version)/65536) 								
									Print.info("- Version: " + version+' -> '+content_name+' ('+str(v_number)+')')
									Print.info("- Type: " + content_type)								
									if content_name == 'AddOnContent':
										upd_number=int(RSversion/65536) 
										Print.info(reqtag + str(RSversion)+' -> ' +'patch'+' ('+str(upd_number)+')')																		
									else:
										Print.info(reqtag + str(RSversion)+" -> " +RSV_rq)						
									Print.info('- Encryption (keygeneration): ' + str(keygen)+" -> " +FW_rq)
									if content_name != 'AddOnContent':							
										Print.info('- Patchable to: ' + str(MinRSV)+" -> " + RSV_rq_min)
									else:
										Print.info('- Patchable to: DLC -> no RSV to patch')									
						
	def inf_get_title(self,target,offset,content_entries,original_ID):
		content_type=''
		token='secure'		
		for nspF in self.hfs0:
			if token == str(nspF._path):
				for nca in nspF:
					if type(nca) == Nca:
						if target ==  str(nca._path):
							for f in nca:
								for cnmt in f:
									nca.rewind()
									f.rewind()
									cnmt.rewind()					
									cnmt.seek(0x20+offset)	
									nca_name='false'
									for i in range(content_entries):
										vhash = cnmt.read(0x20)
										NcaId = cnmt.read(0x10)
										size = cnmt.read(0x6)
										ncatype = cnmt.read(0x1)
										unknown = cnmt.read(0x1)
										ncatype2 = int.from_bytes(ncatype, byteorder='little')
										if ncatype2 == 3:
											nca_name=str(hx(NcaId))
											nca_name=nca_name[2:-1]+'.nca'
											content_name=str(cnmt._path)
											content_name=content_name[:-22]
											if content_name == 'Patch':
												content_type=' [UPD]'
		if nca_name=='false':
			for nspF in self.hfs0:
				if token == str(nspF._path):
					for nca in nspF:		
						if type(nca) == Nca:
							if 	str(nca.header.contentType) == 'Content.META':
								for f in nca:
									for cnmt in f:
										cnmt.rewind()
										testID=cnmt.readInt64()
										if 	testID == original_ID:
											nca.rewind()
											f.rewind()								
											titleid=cnmt.readInt64()
											titleversion = cnmt.read(0x4)
											cnmt.rewind()
											cnmt.seek(0xE)
											offset=cnmt.readInt16()
											content_entries=cnmt.readInt16()
											meta_entries=cnmt.readInt16()
											cnmt.rewind()
											cnmt.seek(0x20)
											original_ID=cnmt.readInt64()
											min_sversion=self.readInt32()
											end_of_emeta=self.readInt32()	
											target=str(nca._path)
											contentname = self.splitter_get_title(target,offset,content_entries,original_ID)
											cnmt.rewind()
											cnmt.seek(0x20+offset)								
											for i in range(content_entries):
												vhash = cnmt.read(0x20)
												NcaId = cnmt.read(0x10)
												size = cnmt.read(0x6)
												ncatype = cnmt.read(0x1)
												unknown = cnmt.read(0x1)
												ncatype2 = int.from_bytes(ncatype, byteorder='little')
												if ncatype2 == 3:
													nca_name=str(hx(NcaId))
													nca_name=nca_name[2:-1]+'.nca'
													content_type=' [DLC]'
		title = 'DLC'									
		for nspF in self.hfs0:
			if token == str(nspF._path):
				for nca in nspF:		
					if type(nca) == Nca:
						if nca_name == str(nca._path):
							for f in nca:
								nca.rewind()
								f.rewind()	
								f.seek(0x14200)
								for i in range(14):
									title = f.read(0x200)		
									title = title.split(b'\0', 1)[0].decode('utf-8')
									title = (re.sub(r'[\/\\\:\*\?\!\"\<\>\|\.\s™©®()\~]+', ' ', title))
									title = title.strip()
									if title == "":
										title = 'DLC'
									if title != 'DLC':
										title = title
										return(title)
		return(title)			
												
						