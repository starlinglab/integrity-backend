from .context import numbers


def test_create_asset_tree():
    asset_filepath = '/tmp/549e6b0161de2803df054b9e8575311f93f754b5366096a16a58494d0fc36044.encrypted'
    asset_creator_filepath = '/tmp/identity.json'
    nft_record_filepath = '/tmp/nftRecord.json'
    asset_tree = numbers.Numbers.create_asset_tree(asset_filepath=asset_filepath,
                                                   asset_creator_filepath=asset_creator_filepath,
                                                   nft_record_filepath=nft_record_filepath)
    print(f'Asset Tree: {asset_tree}')

def test_sign_integrity_hash():
    private_key = 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
    sha256sum = '31273f1efbcf53703e8b79a5a68019ca8f13568e50cce755d7645b1a52dc560d'
    signature = numbers.Numbers.sign_message(sha256sum, private_key)
    assert signature == '0x39b978b6eb17aab3b4614cc13c7b1146e6a7384c3197622a8b58d3a72b8b63cc460b13781e6b3acc7647753f61e2bc1002ebe88d08b119f1c5fb9e49bf7e66e81b'

def test_verify_integrity_hash():
    sha256sum = '31273f1efbcf53703e8b79a5a68019ca8f13568e50cce755d7645b1a52dc560d'
    signature = '0x39b978b6eb17aab3b4614cc13c7b1146e6a7384c3197622a8b58d3a72b8b63cc460b13781e6b3acc7647753f61e2bc1002ebe88d08b119f1c5fb9e49bf7e66e81b'
    signer_address = numbers.Numbers.verify_message(sha256sum, signature)
    assert signer_address == '0x8fd379246834eac74B8419FfdA202CF8051F7A03'

def test_mint_nft():
    receiver_address = '0x76557Ea1C655CeACc79f2dd920DFF50b296808eB'
    metadata = {
      'name': 'MeiMei Fried Chicken',
      'description': 'Taiwanese dog MeiMei is waiting for fried chicken',
      'image': 'https://ipfs.io/ipfs/bafybeifhtlxx7hxisn3pgpn743azzu6qisrr6q3pednauipkv4a6mrn4yu',
      'animation_url': 'https://ipfs.io/ipfs/bafybeifhtlxx7hxisn3pgpn743azzu6qisrr6q3pednauipkv4a6mrn4yu',
      'external_url': 'https://authmedia.net/asset-profile?cid=bafybeid57qjbb2j44n32xhmox3r2cwlndhazihjwiknefs6ldch57hlcoy'
    }
    nft_record = numbers.Numbers.mint_nft(receiver_address, metadata)
    print(f'NFT Record: {nft_record}')

def test_commit():
    asset_filepath = '/tmp/549e6b0161de2803df054b9e8575311f93f754b5366096a16a58494d0fc36044.encrypted'
    asset_tree_filepath = '/tmp/assetTree.json'
    author_filepath = '/tmp/identity.json'
    action_filepath = '/tmp/action.json'
    tx_hash = numbers.Numbers.commit(asset_filepath,
                                     asset_tree_filepath,
                                     author_filepath,
                                     action_filepath,
                                     abstract='',
                                     create_signature=True,
                                     private_key='aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa')
    print(f'Commit Tx hash: {tx_hash}')